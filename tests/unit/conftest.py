from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never read this machine's settings.json, Claude Code settings or AWS credentials."""
    monkeypatch.setenv("INDO_SETTINGS_FILE", str(tmp_path / "settings.json"))
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", "AWS_DEFAULT_REGION"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "aws-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "aws-credentials"))


class FakeMessages:
    """Records calls and returns canned replies, standing in for client.messages."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        # Copy history: callers append to the list after the call returns.
        self.calls.append({**kwargs, "messages": [dict(m) for m in kwargs["messages"]]})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        text, stop = reply if isinstance(reply, tuple) else (reply, "end_turn")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop)


@pytest.fixture
def fake_client():
    def make(*replies):
        messages = FakeMessages(replies or ["A draft."])
        # Current Claude models go through client.beta.messages (refusal fallbacks); both record to one list.
        return SimpleNamespace(messages=messages, beta=SimpleNamespace(messages=messages))
    return make


class FakeChat:
    """Stands in for llm._OpenAICompatible: records request bodies, returns canned replies."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, body):
        self.calls.append(body)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        text, finish = reply if isinstance(reply, tuple) else (reply, "stop")
        return {"choices": [{"message": {"content": text}, "finish_reason": finish}]}


@pytest.fixture
def fake_chat():
    def make(*replies):
        return FakeChat(replies or ["A draft."])
    return make


@pytest.fixture
def draft_request():
    return {
        "activity": "post",
        "topic": "Won second place at the Kochi GenAI hackathon",
        "when": "12-14 Oct 2026",
        "source": {"type": "skip"},
        "people": [{"name": "Asha Menon", "url": "https://www.linkedin.com/in/asha", "bio": "Mentor"}],
    }


@pytest.fixture
def llm_request(draft_request):
    return {**draft_request, "engine": "llm", "provider": "anthropic"}
