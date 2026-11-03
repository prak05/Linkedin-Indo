import json
import os
import stat

import pytest

from indo_core import llm, settings
from indo_core.validation import ValidationError


def test_saved_key_is_private_masked_and_exported(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setitem(settings._ORIGINAL_ENV, "ANTHROPIC_API_KEY", None)
    v = settings.save({"keys": {"anthropic": "sk-ant-secret-1234"}})
    assert v["keys"]["anthropic"] == {"set": True, "source": "settings", "hint": "…1234"}
    assert "sk-ant-secret-1234" not in json.dumps(v)
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-secret-1234"
    assert stat.S_IMODE(os.stat(settings.path()).st_mode) == 0o600
    # An empty string clears it again.
    settings.save({"keys": {"anthropic": ""}})
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_omitted_fields_keep_their_saved_value():
    settings.save({"bedrock": {"region": "us-west-2", "access_key_id": "AKIAEXAMPLE1234", "secret_access_key": "s"}})
    settings.save({"bedrock": {"profile": "work"}})
    b = settings.bedrock()
    assert b["region"] == "us-west-2" and b["access_key_id"] == "AKIAEXAMPLE1234" and b["profile"] == "work"


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        settings.save({"keys": {"nope": "x"}})
    with pytest.raises(ValidationError):
        settings.save({"bedrock": {"password": "x"}})


def test_import_from_claude_code(tmp_path):
    src = tmp_path / "claude.json"
    src.write_text(json.dumps({"env": {"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_REGION": "us-west-2",
                                       "AWS_ACCESS_KEY_ID": "AKIA1111", "AWS_SECRET_ACCESS_KEY": "sec",
                                       "AWS_SESSION_TOKEN": "tok"}}))
    settings.save({"bedrock": {"profile": "old"}})
    v = settings.import_claude_code(src)
    b = settings.bedrock()
    assert b == {"region": "us-west-2", "profile": "", "access_key_id": "AKIA1111",
                 "secret_access_key": "sec", "session_token": "tok"}
    assert "temporary" in v["notes"][0]
    empty = tmp_path / "empty.json"
    empty.write_text("{}")
    with pytest.raises(ValidationError):
        settings.import_claude_code(empty)


def test_bedrock_client_uses_saved_keys_or_profile(monkeypatch):
    seen = {}

    class FakeBedrock:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    import anthropic
    monkeypatch.setattr(anthropic, "AnthropicBedrock", FakeBedrock)
    settings.save({"bedrock": {"region": "eu-central-1", "profile": "work"}})
    llm.get_client("bedrock")
    assert seen["aws_region"] == "eu-central-1" and seen["aws_profile"] == "work" and seen["timeout"] == llm.TIMEOUT
    seen.clear()
    settings.save({"bedrock": {"access_key_id": "AKIA2", "secret_access_key": "s2"}})
    llm.get_client("bedrock")
    assert seen["aws_access_key"] == "AKIA2" and seen["aws_secret_key"] == "s2" and "aws_profile" not in seen
    assert llm.bedrock_ready() is True


def test_bedrock_operation_not_allowed_explains_the_account_block(fake_client, monkeypatch):
    import anthropic
    import httpx2

    req = httpx2.Request("POST", "https://bedrock-runtime.us-east-1.amazonaws.com/model/x/invoke")
    err = anthropic.BadRequestError("Operation not allowed", response=httpx2.Response(400, request=req),
                                    body={"message": "Operation not allowed"})
    r = llm.test_connection("bedrock", client=fake_client(err))
    assert r["ok"] is False and "account restriction" in r["message"]
    r = llm.test_connection("bedrock", client=fake_client("OK"))
    assert r["ok"] is True and r["model"] == "us.anthropic.claude-opus-5-5"
