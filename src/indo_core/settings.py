"""App settings: API keys, Amazon Bedrock credentials and the agent workspace.

Saved from the Settings panel, so the LLM engine works when the app is started
from the apps menu (no terminal, no exported variables). The file is
settings.json next to the persona folder (INDO_SETTINGS_FILE overrides it),
mode 0600, and never leaves this machine. A key saved here wins over the same
variable in the environment; an empty field falls back to the environment.
"""

import json
import os
from pathlib import Path

from .validation import ValidationError, _text

# Provider id -> environment variable that llm.py reads.
KEY_ENVS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
BEDROCK_FIELDS = ("region", "profile", "access_key_id", "secret_access_key", "session_token")
BEDROCK_AGENT_FIELDS = ("agent_id", "agent_alias_id")
BEDROCK_SECRETS = ("access_key_id", "secret_access_key", "session_token")
CLAUDE_CODE_SETTINGS = Path.home() / ".claude" / "settings.json"

# Environment values present before any settings were applied, so clearing a key restores them.
_ORIGINAL_ENV = {env: os.environ.get(env) for env in KEY_ENVS.values()}


def path():
    if os.environ.get("INDO_SETTINGS_FILE"):
        return Path(os.environ["INDO_SETTINGS_FILE"])
    from .persona import folder
    return folder().parent / "settings.json"


def default_workspace():
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return str(base / "linkedin-indo" / "workspace")


def load():
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    keys = data.get("keys") if isinstance(data.get("keys"), dict) else {}
    bedrock = data.get("bedrock") if isinstance(data.get("bedrock"), dict) else {}
    agent_cfg = data.get("bedrock_agent") if isinstance(data.get("bedrock_agent"), dict) else {}
    return {
        "keys": {p: str(keys.get(p) or "") for p in KEY_ENVS},
        "bedrock": {f: str(bedrock.get(f) or "") for f in BEDROCK_FIELDS},
        "bedrock_agent": {f: str(agent_cfg.get(f) or "") for f in BEDROCK_AGENT_FIELDS},
        "workspace": str(data.get("workspace") or default_workspace()),
    }


def _write(data):
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    # Create private from the start: the file holds API keys.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    tmp.replace(target)


def _hint(secret):
    return f"…{secret[-4:]}" if len(secret) > 8 else "set"


def view():
    """For GET /settings: what is configured, with secrets masked."""
    s = load()
    keys = {}
    for provider, env in KEY_ENVS.items():
        saved = s["keys"][provider]
        from_env = _ORIGINAL_ENV.get(env)
        keys[provider] = {"set": bool(saved or from_env), "source": "settings" if saved else "environment" if from_env else None,
                          "hint": _hint(saved or from_env) if saved or from_env else ""}
    b = s["bedrock"]
    bedrock = {"region": b["region"], "profile": b["profile"],
               "keys_saved": bool(b["access_key_id"] and b["secret_access_key"]),
               "key_hint": _hint(b["access_key_id"]) if b["access_key_id"] else "",
               "session_token": bool(b["session_token"])}
    return {"keys": keys, "bedrock": bedrock, "bedrock_agent": s.get("bedrock_agent", {}),
            "workspace": s["workspace"], "file": str(path()),
            "claude_code_settings": CLAUDE_CODE_SETTINGS.is_file()}


def save(payload):
    """POST /settings. A field left out (or null) keeps its saved value; an empty string clears it."""
    if not isinstance(payload, dict):
        raise ValidationError("Send settings as a JSON object.")
    s = load()
    for provider, value in (payload.get("keys") or {}).items():
        if provider not in KEY_ENVS:
            raise ValidationError(f"Unknown provider '{provider}'.")
        if value is not None:
            s["keys"][provider] = _text(value, f"{provider} key", required=False, max_len=500) or ""
    for field, value in (payload.get("bedrock") or {}).items():
        if field not in BEDROCK_FIELDS:
            raise ValidationError(f"Unknown Bedrock setting '{field}'.")
        if value is not None:
            s["bedrock"][field] = _text(value, f"Bedrock {field}", required=False, max_len=4000) or ""
    for field, value in (payload.get("bedrock_agent") or {}).items():
        if field in BEDROCK_AGENT_FIELDS and value is not None:
            s["bedrock_agent"][field] = _text(value, f"Bedrock Agent {field}", required=False, max_len=200) or ""
    if payload.get("workspace") is not None:
        ws = _text(payload["workspace"], "Workspace", required=False, max_len=500)
        s["workspace"] = str(Path(ws).expanduser()) if ws else default_workspace()
    _write(s)
    apply(s)
    return view()


def bedrock_agent():
    return load()["bedrock_agent"]


def import_claude_code(source=None):
    """Copy the AWS / Anthropic credentials from Claude Code's settings (only when the user asks)."""
    source = Path(source or CLAUDE_CODE_SETTINGS)
    try:
        env = json.loads(source.read_text(encoding="utf-8")).get("env") or {}
    except (OSError, ValueError):
        raise ValidationError(f"Could not read {source}.") from None
    bedrock = {"region": env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION"), "profile": env.get("AWS_PROFILE"),
               "access_key_id": env.get("AWS_ACCESS_KEY_ID"), "secret_access_key": env.get("AWS_SECRET_ACCESS_KEY"),
               "session_token": env.get("AWS_SESSION_TOKEN")}
    bedrock = {k: v for k, v in bedrock.items() if v}
    keys = {"anthropic": env["ANTHROPIC_API_KEY"]} if env.get("ANTHROPIC_API_KEY") else {}
    if not bedrock and not keys:
        raise ValidationError("Claude Code's settings have no AWS or Anthropic credentials to import.")
    if bedrock.get("access_key_id"):
        # Explicit keys replace any saved profile and stale token.
        bedrock = {"profile": "", "session_token": "", **bedrock}
    result = save({"keys": keys, "bedrock": bedrock})
    found = (["Bedrock credentials"] if bedrock else []) + (["Anthropic API key"] if keys else [])
    note = " and ".join(found) + " imported."
    if bedrock.get("session_token"):
        note += " These are temporary AWS credentials: import again when they expire."
    return {**result, "notes": [note]}


def apply(s=None):
    """Export saved API keys so llm.py (which reads the environment) sees them."""
    s = s or load()
    for provider, env in KEY_ENVS.items():
        value = s["keys"][provider] or _ORIGINAL_ENV.get(env)
        if value:
            os.environ[env] = value
        else:
            os.environ.pop(env, None)


def bedrock():
    """Saved Bedrock settings (empty strings for anything not set)."""
    return load()["bedrock"]
