"""LLM engine: generate and revise drafts through a hosted model API (FR-7, FR-8).

Providers:
- anthropic: Claude through the Anthropic API (ANTHROPIC_API_KEY).
- bedrock:   Claude on Amazon Bedrock (bedrock-runtime, cross-region inference profiles such as
             us.anthropic.claude-opus-5-5). Credentials come from Settings (keys or a profile),
             else the normal AWS chain (~/.aws, AWS_* variables).
- openai, gemini, groq, openrouter, ollama: any OpenAI-compatible chat API.

History is kept in Anthropic message format (the caller sends it back for each
revision) and converted per provider on every call, so the provider or model can
be changed between revisions.
"""

import json
import os
import urllib.error
import urllib.request

from . import settings
from .errors import DraftError
from .persona import similar_posts, structure
from .prompt import load_samples, request_text, system_prompt
from .sources import build_source, extract_text
from .validation import ValidationError

MAX_TOKENS = 16000
EFFORT = "medium"
# A full post from a current Claude model can take well over 25 s; Lambda passes its own shorter limit.
TIMEOUT = 120.0
DEFAULT_AWS_REGION = "us-east-1"

PROVIDERS = {
    "anthropic": {"label": "Anthropic (Claude)", "kind": "anthropic", "key_env": "ANTHROPIC_API_KEY",
                  "default": "claude-opus-5-5",
                  "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1"]},
    # Bedrock serves current Claude models only through inference profiles: a geography prefix
    # (us., eu., apac.) or global. Bare anthropic.* IDs are rejected for on-demand use.
    "bedrock": {"label": "Amazon Bedrock (Claude)", "kind": "bedrock", "key_env": None,
                "default": "{geo}.anthropic.claude-opus-5-5",
                "models": ["{geo}.anthropic.claude-3-5-sonnet-20241022-v2:0",
                           "{geo}.anthropic.claude-3-7-sonnet-20250219-v1:0",
                           "{geo}.anthropic.claude-opus-5-5", "{geo}.anthropic.claude-sonnet-5-5",
                           "{geo}.anthropic.claude-haiku-5-5", "{geo}.anthropic.claude-fable-5-1",
                           "anthropic.claude-3-5-haiku-20241022-v1:0", "anthropic.claude-3-haiku-20240307-v1:0",
                           "bedrock-agent",
                           "global.anthropic.claude-opus-5-5", "global.anthropic.claude-sonnet-5-5"]},
    "openai": {"label": "OpenAI", "kind": "openai", "key_env": "OPENAI_API_KEY",
               "base_url": "https://api.openai.com/v1", "default": "gpt-5", "models": ["gpt-5", "gpt-5-mini"]},
    "gemini": {"label": "Google Gemini", "kind": "openai", "key_env": "GEMINI_API_KEY",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "default": "gemini-2.5-flash", "models": ["gemini-2.5-flash", "gemini-2.5-pro"]},
    "groq": {"label": "Groq", "kind": "openai", "key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1",
             "default": "llama-3.3-70b-versatile", "models": ["llama-3.3-70b-versatile"]},
    "openrouter": {"label": "OpenRouter", "kind": "openai", "key_env": "OPENROUTER_API_KEY",
                   "base_url": "https://openrouter.ai/api/v1", "default": "openrouter/auto", "models": ["openrouter/auto"]},
    "ollama": {"label": "Ollama (this machine)", "kind": "openai", "key_env": None,
               "base_url": "http://127.0.0.1:11434/v1", "default": "llama3.2", "models": ["llama3.2"]},
}
DEFAULT_PROVIDER = "anthropic"
# Current Claude models: effort is set explicitly; the first three also get server-side refusal fallbacks.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"}
EFFORT_MODELS = FALLBACK_MODELS | {"claude-haiku-5-5"}


def bedrock_region():
    b = settings.bedrock()
    if b["region"]:
        return b["region"]
    if os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"):
        return os.environ.get("AWS_REGION") or os.environ["AWS_DEFAULT_REGION"]
    return _aws_config(b["profile"]).get("region") or DEFAULT_AWS_REGION


def _aws_config(profile=None):
    """The profile's section of ~/.aws/config. Reads files only: boto3's own lookups can wait seconds
    on the EC2 metadata service, and /health must answer fast."""
    try:
        import botocore.session
        return botocore.session.Session(profile=profile or None).get_scoped_config()
    except Exception:  # noqa: BLE001 - botocore missing or an unknown profile
        return {}


def _geo(region):
    return {"eu": "eu", "ap": "apac"}.get(region.split("-", 1)[0], "us")


def bedrock_model(model):
    """Expand {geo} and upgrade a bare anthropic.* ID to this region's inference profile."""
    geo = _geo(bedrock_region())
    model = model.replace("{geo}", geo)
    return f"{geo}.{model}" if model.startswith("anthropic.") else model


def bedrock_ready():
    """Credentials are configured somewhere (saved keys, AWS_* variables or a profile in ~/.aws).
    Whether AWS accepts them shows on the first call, or with Settings, Test connection."""
    b = settings.bedrock()
    if (b["access_key_id"] and b["secret_access_key"]) or (
            os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
        return True
    try:
        import botocore.session
        session = botocore.session.Session()
        return (b["profile"] or os.environ.get("AWS_PROFILE") or "default") in session.available_profiles
    except Exception:  # noqa: BLE001 - no botocore
        return False


def provider_id(name=None):
    name = name or os.environ.get("INDO_PROVIDER") or DEFAULT_PROVIDER
    if name not in PROVIDERS:
        raise ValidationError(f"Unknown provider '{name}'. Use one of: {', '.join(PROVIDERS)}.")
    return name


def model_id(provider=None, model=None):
    provider = provider_id(provider)
    env = f"INDO_{provider.upper()}_MODEL"
    # INDO_MODEL is the original single-provider setting, kept for the Anthropic provider.
    legacy = os.environ.get("INDO_MODEL") if provider == "anthropic" else None
    chosen = model or os.environ.get(env) or legacy or PROVIDERS[provider]["default"]
    return bedrock_model(chosen) if provider == "bedrock" else chosen


def providers():
    """For GET /health and the UI: what can be chosen, and which providers have credentials."""
    out = {}
    for name, p in PROVIDERS.items():
        if name == "bedrock":
            ready, models = bedrock_ready(), [bedrock_model(m) for m in p["models"]]
        else:
            ready, models = (bool(os.environ.get(p["key_env"])) if p["key_env"] else True), p["models"]
        out[name] = {"label": p["label"], "models": models, "default": model_id(name), "ready": ready}
    return out


def get_client(provider=None, api_key=None, timeout=TIMEOUT, max_retries=1):
    """Create the client for a provider. Lambda passes a shorter timeout to fit API Gateway's 30 s limit."""
    provider = provider_id(provider)
    p = PROVIDERS[provider]
    if p["kind"] == "openai":
        key = api_key or (os.environ.get(p["key_env"]) if p["key_env"] else "none")
        if not key:
            raise DraftError(f"{p['key_env']} is not set on the backend.", 500)
        base = os.environ.get(f"INDO_{provider.upper()}_BASE_URL") or p["base_url"]
        return _OpenAICompatible(base, key, timeout)
    try:
        import anthropic
    except ImportError:
        raise DraftError("The anthropic package is not installed. Run: python3.13 -m pip install --user -r requirements.txt", 500) from None
    if p["kind"] == "bedrock":
        b = settings.bedrock()
        creds = {"aws_profile": b["profile"]} if b["profile"] else {}
        if b["access_key_id"] and b["secret_access_key"]:
            creds = {"aws_access_key": b["access_key_id"], "aws_secret_key": b["secret_access_key"],
                     "aws_session_token": b["session_token"] or None}
        return anthropic.AnthropicBedrock(aws_region=bedrock_region(), timeout=timeout, max_retries=max_retries, **creds)
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise DraftError("ANTHROPIC_API_KEY is not set on the backend.", 500)
    return anthropic.Anthropic(api_key=key, timeout=timeout, max_retries=max_retries)


def invoke_bedrock_agent(input_text: str, agent_id: str | None = None, alias_id: str | None = None, session_id: str = "linkedin-indo-session") -> str:
    """Invoke an AWS Bedrock Agent directly using boto3 bedrock-agent-runtime."""
    import boto3
    b = settings.bedrock()
    a_id = agent_id or b.get("agent_id") or os.environ.get("AWS_BEDROCK_AGENT_ID")
    al_id = alias_id or b.get("agent_alias_id") or os.environ.get("AWS_BEDROCK_AGENT_ALIAS_ID") or "TSTALIASID"
    if not a_id:
        raise DraftError("AWS Bedrock Agent ID is not configured. Set it in Settings.", 400)

    kwargs = {"region_name": bedrock_region()}
    if b.get("profile"):
        import botocore.session
        sess = botocore.session.Session(profile=b["profile"])
        kwargs["botocore_session"] = sess
    elif b.get("access_key_id") and b.get("secret_access_key"):
        kwargs["aws_access_key_id"] = b["access_key_id"]
        kwargs["aws_secret_access_key"] = b["secret_access_key"]
        if b.get("session_token"):
            kwargs["aws_session_token"] = b["session_token"]

    try:
        client = boto3.client("bedrock-agent-runtime", **kwargs)
        response = client.invoke_agent(
            agentId=a_id,
            agentAliasId=al_id,
            sessionId=session_id,
            inputText=input_text
        )
        parts = []
        for event in response.get("completion", []):
            chunk = event.get("chunk")
            if chunk and "bytes" in chunk:
                parts.append(chunk["bytes"].decode("utf-8", errors="replace"))
        return "".join(parts).strip()
    except Exception as e:
        raise DraftError(f"Bedrock Agent error: {e}", 502) from None



def _call_claude(client, provider, model, system, messages):
    import anthropic

    kwargs = {"model": model, "max_tokens": MAX_TOKENS, "system": system, "messages": messages}
    bare = model.split("anthropic.", 1)[-1]
    if bare in EFFORT_MODELS:
        kwargs["output_config"] = {"effort": EFFORT}
    try:
        if provider == "anthropic" and model in FALLBACK_MODELS:
            response = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        else:
            response = client.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        raise DraftError("The Anthropic API key was rejected." if provider == "anthropic"
                         else "AWS rejected the credentials for Bedrock.", 502) from None
    except anthropic.PermissionDeniedError as e:
        detail = error_detail(e)
        raise DraftError(f"This account cannot use {model}. On Bedrock, enable model access first."
                         + (f" AWS says: {detail}" if detail else ""), 403) from None
    except anthropic.NotFoundError:
        raise DraftError(f"The model {model} was not found on {PROVIDERS[provider]['label']}.", 400) from None
    except anthropic.RateLimitError:
        raise DraftError("Claude is rate limited right now. Try again in a minute.", 503) from None
    except anthropic.BadRequestError as e:
        detail = error_detail(e) or "the input could not be processed"
        if provider == "bedrock" and "operation not allowed" in detail.lower():
            raise DraftError(BEDROCK_BLOCKED, 403) from None
        raise DraftError(f"Claude rejected the request: {detail}", 400) from None
    except anthropic.APITimeoutError:
        raise DraftError("Claude took too long to answer. Try again.", 504) from None
    except anthropic.APIConnectionError:
        raise DraftError(f"Could not reach {PROVIDERS[provider]['label']}. Check the internet connection.", 502) from None
    except anthropic.APIStatusError as e:
        raise DraftError(f"{PROVIDERS[provider]['label']} returned an error ({e.status_code}). Try again.", 502) from None
    except anthropic.AnthropicError:
        raise DraftError("The draft could not be generated.", 502) from None

    if response.stop_reason == "refusal":
        raise DraftError("Claude declined to write this draft. Try rephrasing the topic.", 422)
    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()
    if not text:
        raise DraftError("Claude returned an empty draft. Try again.", 502)
    notes = ["The draft hit the length limit and may be cut off."] if response.stop_reason == "max_tokens" else []
    return text, notes


BEDROCK_BLOCKED = ("AWS answered 'Operation not allowed': this AWS account cannot call Claude on Bedrock yet. "
                   "This is an account restriction, not a model setting. New accounts often need a valid payment "
                   "method, a Bedrock quota increase or an AWS support case. Open Settings to use other AWS "
                   "credentials, or pick another provider.")


def error_detail(e):
    """The provider's own error message from an anthropic.APIStatusError, if it sent one."""
    body = e.body if isinstance(getattr(e, "body", None), dict) else {}
    err = body.get("error")
    return ((err.get("message") if isinstance(err, dict) else None) or body.get("message") or "").strip()


def test_connection(provider=None, model=None, client=None):
    """POST /settings/test: one tiny request. Returns {"ok", "message", "model"}; never raises DraftError."""
    import time

    try:
        provider = provider_id(provider)
        model = model_id(provider, model)
        start = time.monotonic()
        text, _ = _call(client or get_client(provider, timeout=60.0, max_retries=0), provider, model,
                        "Reply with the single word OK.", [{"role": "user", "content": "Connection test."}])
    except (DraftError, ValidationError) as e:
        return {"ok": False, "message": str(e), "model": model if isinstance(model, str) else None}
    return {"ok": True, "model": model,
            "message": f"{PROVIDERS[provider]['label']} answered in {time.monotonic() - start:.1f} s with {model}."}


class _OpenAICompatible:
    """Minimal client for OpenAI-compatible /chat/completions endpoints (stdlib only)."""

    def __init__(self, base_url, api_key, timeout):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, body):
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


def _openai_messages(system, messages, notes):
    """Convert Anthropic-format history. PDFs become extracted text; images become data URLs."""
    out = [{"role": "system", "content": system}]
    for msg in messages:
        if isinstance(msg["content"], str):
            out.append({"role": msg["role"], "content": msg["content"]})
            continue
        parts = []
        for block in msg["content"]:
            if block["type"] == "text":
                parts.append({"type": "text", "text": block["text"]})
            elif block["type"] == "image":
                src = block["source"]
                parts.append({"type": "image_url", "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
            elif block["type"] == "document":
                text, problem = extract_text("document", block["source"]["data"])
                if text:
                    parts.append({"type": "text", "text": f"<event_material>\n{text}\n</event_material>"})
                else:
                    notes.append(f"The PDF could not be read for this provider: {problem}.")
        out.append({"role": msg["role"], "content": parts})
    return out


def _call_openai(client, provider, model, system, messages):
    notes = []
    body = {"model": model, "max_tokens": MAX_TOKENS, "messages": _openai_messages(system, messages, notes)}
    label = PROVIDERS[provider]["label"]
    try:
        data = client.chat(body)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise DraftError(f"{label} rejected the API key.", 502) from None
        if e.code == 404:
            raise DraftError(f"The model {model} was not found on {label}.", 400) from None
        if e.code == 429:
            raise DraftError(f"{label} is rate limited right now. Try again in a minute.", 503) from None
        raise DraftError(f"{label} returned an error ({e.code}). Try again.", 502) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise DraftError(f"Could not reach {label}.", 502) from None
    except ValueError:
        raise DraftError(f"{label} sent a response that is not JSON.", 502) from None
    try:
        choice = data["choices"][0]
        text = (choice["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise DraftError(f"{label} sent an unexpected response.", 502) from None
    if not text:
        raise DraftError(f"{label} returned an empty draft. Try again.", 502)
    if choice.get("finish_reason") == "length":
        notes.append("The draft hit the length limit and may be cut off.")
    return text, notes


def _call(client, provider, model, system, messages):
    if PROVIDERS[provider]["kind"] == "openai":
        return _call_openai(client, provider, model, system, messages)
    return _call_claude(client, provider, model, system, messages)


def _first_text(history):
    first = history[0]["content"]
    return first if isinstance(first, str) else " ".join(b.get("text", "") for b in first if b.get("type") == "text")


def _engine_note(provider, model):
    return f"Written by {model} via {PROVIDERS[provider]['label']}."


def style_examples(topic, samples=None, persona=None, posts=None):
    """Style examples: your past posts most like this topic, else the persona's showcase, else samples/."""
    if posts:
        return similar_posts(topic, posts)
    if persona and persona.get("showcase"):
        return persona["showcase"][:3]
    return load_samples() if samples is None else samples


def generate(req, client=None, samples=None, fetch=None, provider=None, model=None,
             persona=None, posts=None, inspiration=None):
    """req is a validated draft request. Returns {"draft", "history", "notes"}."""
    provider = provider_id(provider)
    model = model_id(provider, model)
    blocks, event_text, notes = build_source(req["source"], **({"fetch": fetch} if fetch else {}))
    samples = style_examples(req["topic"], samples, persona, posts)
    if not samples and not persona:
        notes.append("No persona or style samples yet, so the draft uses a neutral voice. Set up your persona first.")
    shape = structure(inspiration["text"]) if inspiration else None
    content = blocks + [{"type": "text", "text": request_text(req, event_text, shape)}]
    history = [{"role": "user", "content": content}]
    from .prompt import system_prompt_with_rag
    sys_prompt = system_prompt_with_rag(samples, persona, topic=req.get("topic"))
    draft, more = _call(client or get_client(provider), provider, model, sys_prompt, history)
    history.append({"role": "assistant", "content": draft})
    return {"draft": draft, "history": history, "notes": notes + more + [_engine_note(provider, model)]}


def revise(req, client=None, samples=None, provider=None, model=None, persona=None, posts=None):
    """req is a validated revise request. Returns {"draft", "history", "notes"}."""
    provider = provider_id(provider)
    model = model_id(provider, model)
    topic = _first_text(req["history"])
    samples = style_examples(topic, samples, persona, posts)
    history = req["history"] + [{"role": "user", "content": req["feedback"]}]
    from .prompt import system_prompt_with_rag
    sys_prompt = system_prompt_with_rag(samples, persona, topic=topic)
    draft, notes = _call(client or get_client(provider), provider, model, sys_prompt, history)
    history.append({"role": "assistant", "content": draft})
    return {"draft": draft, "history": history, "notes": notes + [_engine_note(provider, model)]}
