from types import SimpleNamespace

import pytest

from indo_core import agent, settings
from indo_core.validation import ValidationError


class FakeAgentClient:
    """Returns canned (content blocks, stop_reason) replies; records each request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self
        self.beta = SimpleNamespace(messages=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content, stop = self.replies.pop(0)
        return SimpleNamespace(content=[SimpleNamespace(**b) for b in content], stop_reason=stop)


def tool(name, id_, **inp):
    return {"type": "tool_use", "id": id_, "name": name, "input": inp}


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    settings.save({"workspace": str(root)})
    return root


def run(payload, client, ws, tmp_path):
    return agent.step({"provider": "anthropic", **payload}, client=client, persona_dir=tmp_path / "persona",
                      posts_dir=tmp_path / "posts")


def test_read_only_tools_run_without_approval(ws, tmp_path, monkeypatch):
    (ws).mkdir(parents=True, exist_ok=True)
    (ws / "notes.md").write_text("hello from a file")
    client = FakeAgentClient(([tool("read_file", "t1", path="notes.md")], "tool_use"),
                             ([{"type": "text", "text": "It says hello."}], "end_turn"))
    r = run({"messages": [{"role": "user", "content": "What is in notes.md?"}]}, client, ws, tmp_path)
    assert r["next"] == "continue" and r["messages"][-1]["role"] == "assistant"
    # Tools are declared, effort set, and fallbacks used on the Anthropic API.
    call = client.calls[0]
    assert {t["name"] for t in call["tools"]} >= {"web_search", "run_command"} and call["fallbacks"] == "default"
    r = run({"messages": r["messages"]}, client, ws, tmp_path)
    result = r["messages"][-1]["content"][0]
    assert r["next"] == "continue" and result["tool_use_id"] == "t1" and result["content"] == "hello from a file"
    r = run({"messages": r["messages"]}, client, ws, tmp_path)
    assert r["next"] == "done" and r["messages"][-1]["content"][0]["text"] == "It says hello."


def test_commands_wait_for_approval_and_denial_is_reported(ws, tmp_path):
    client = FakeAgentClient(([tool("run_command", "c1", command="echo hi"), tool("list_files", "l1")], "tool_use"))
    r = run({"messages": [{"role": "user", "content": "Say hi"}]}, client, ws, tmp_path)
    assert r["next"] == "approve" and r["pending"] == ["c1"]
    again = run({"messages": r["messages"]}, client, ws, tmp_path)
    assert again["next"] == "approve" and len(again["messages"]) == len(r["messages"])
    denied = run({"messages": r["messages"], "approvals": {"c1": False}}, client, ws, tmp_path)
    results = {b["tool_use_id"]: b for b in denied["messages"][-1]["content"]}
    assert results["c1"]["is_error"] and "declined" in results["c1"]["content"]
    assert "is_error" not in results["l1"]


def test_approved_command_runs_in_the_workspace_without_api_keys(ws, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    client = FakeAgentClient(([tool("run_command", "c1", command="pwd; echo key=$ANTHROPIC_API_KEY")], "tool_use"))
    r = run({"messages": [{"role": "user", "content": "Where am I?"}]}, client, ws, tmp_path)
    r = run({"messages": r["messages"], "approvals": {"c1": True}}, client, ws, tmp_path)
    out = r["messages"][-1]["content"][0]["content"]
    assert "exit code 0" in out and str(ws.resolve()) in out and "sk-should-not-leak" not in out


def test_file_tools_stay_inside_the_workspace(ws):
    with pytest.raises(agent.ToolError):
        agent.read_file("../../etc/passwd")
    agent.write_file("drafts/a.txt", "x")
    assert (ws / "drafts" / "a.txt").read_text() == "x"


def test_agent_needs_a_claude_provider(ws, tmp_path):
    with pytest.raises(ValidationError):
        agent.step({"provider": "openai", "messages": [{"role": "user", "content": "hi"}]})
    with pytest.raises(ValidationError):
        agent.step({"provider": "anthropic", "messages": [{"role": "assistant", "content": "hi"}]})


def test_parse_search_unwraps_result_links():
    page = ('<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&amp;&amp;p=1&amp;u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS9ldmVudA'
            '&amp;ntb=1">AWS <strong>Day</strong></a></h2><p>Kochi, 12 Oct</p></li>')
    assert agent.parse_search(page) == [{"title": "AWS Day", "url": "https://example.com/event", "snippet": "Kochi, 12 Oct"}]
