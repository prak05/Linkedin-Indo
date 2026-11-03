"""Generate and revise drafts with the chosen engine (FR-7, FR-8).

Engines:
- "local": the offline model in local_engine.py. No AI service is called.
- "llm":   a hosted model through llm.py (Claude via Anthropic or Amazon Bedrock,
           or an OpenAI-compatible provider). Pick it with "provider" and "model".

Requests choose with {"engine", "provider", "model"}; INDO_ENGINE sets the default.
Stateless: the caller keeps the history and sends it back for each revision, so
the same code runs in the CLI, the local server and Lambda.
"""

import json
import os

from . import llm, local_engine
from . import persona as persona_mod
from .errors import DraftError
from .validation import ValidationError, _text, validate_draft_request, validate_revise_request

ENGINES = ("local", "llm")
DEFAULT_ENGINE = "local"

__all__ = ["DraftError", "ENGINES", "engine_choice", "generate", "made_locally", "revise", "status"]


def engine_choice(payload=None):
    """Return {"engine", "provider", "model"} from a request, falling back to the environment."""
    payload = payload if isinstance(payload, dict) else {}
    engine = payload.get("engine") or os.environ.get("INDO_ENGINE") or DEFAULT_ENGINE
    if engine not in ENGINES:
        raise ValidationError(f"engine must be one of: {', '.join(ENGINES)}.")
    if engine == "local":
        return {"engine": "local", "provider": None, "model": None}
    provider = llm.provider_id(payload.get("provider"))
    model = _text(payload.get("model"), "Model", required=False, max_len=200) or None
    return {"engine": "llm", "provider": provider, "model": llm.model_id(provider, model)}


def status():
    """For GET /health: the default engine and the LLM providers that can be picked."""
    return {"default_engine": engine_choice()["engine"], "engines": list(ENGINES), "providers": llm.providers()}


def made_locally(history):
    first = history[0].get("content") if history and isinstance(history[0], dict) else None
    if not isinstance(first, str):
        return False
    try:
        return json.loads(first).get("engine") == local_engine.ENGINE
    except (ValueError, AttributeError):
        return False


def _inspiration_notes(draft, inspiration):
    check = persona_mod.originality(draft, inspiration["text"])
    if check["ok"]:
        return [f"Borrowed the structure of the post you liked; originality check passed "
                f"(longest shared phrase: {check['copied_words']} word{'' if check['copied_words'] == 1 else 's'})."]
    return [f"Originality check: the draft repeats \"{check['phrase']}\" from the post you liked. "
            "Ask for another version, or reword it."]


def generate(payload, client=None, samples=None, fetch=None, persona=None, posts=None):
    """POST /drafts. Returns {"draft", "history", "notes", "engine"}.

    persona/posts come from this machine's persona files (local server, CLI); the
    CLOUD backend gets a trimmed persona inside the request instead.
    """
    choice = engine_choice(payload)
    if persona is None and isinstance(payload, dict):
        persona = persona_mod.clean_inline(payload.get("persona"))
    inspiration = persona_mod.validate_inspiration(payload.get("inspiration")) if isinstance(payload, dict) else None
    if choice["engine"] == "local":
        result = local_engine.generate(payload, samples=samples, fetch=fetch, persona=persona, inspiration=inspiration)
    else:
        req = validate_draft_request(payload)
        result = llm.generate(req, client=client, samples=samples, fetch=fetch, provider=choice["provider"],
                              model=choice["model"], persona=persona, posts=posts, inspiration=inspiration)
        if line := persona_mod.credit_line(inspiration):
            result["draft"] = persona_mod.with_credit(result["draft"], line)
            result["history"][-1]["content"] = result["draft"]
    if persona:
        result["notes"].insert(0, f"Written as {persona['answers']['name']} (persona).")
    if inspiration:
        result["notes"] += _inspiration_notes(result["draft"], inspiration)
    return {**result, "engine": choice}


def revise(payload, client=None, samples=None, persona=None, posts=None):
    """POST /drafts/revise. The engine that wrote the draft revises it. Returns {"draft", "history", "notes", "engine"}."""
    history = payload.get("history") if isinstance(payload, dict) else None
    if isinstance(history, list) and made_locally(history):
        return {**local_engine.revise(payload, samples=samples), "engine": engine_choice({"engine": "local"})}
    choice = engine_choice({**(payload if isinstance(payload, dict) else {}), "engine": "llm"})
    if persona is None and isinstance(payload, dict):
        persona = persona_mod.clean_inline(payload.get("persona"))
    req = validate_revise_request(payload)
    result = llm.revise(req, client=client, samples=samples, provider=choice["provider"], model=choice["model"],
                        persona=persona, posts=posts)
    return {**result, "engine": choice}
