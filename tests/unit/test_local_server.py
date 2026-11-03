import http.client
import json
import threading

import pytest

import local_server


@pytest.fixture
def server(tmp_path, fake_client, monkeypatch):
    client = fake_client("Draft one", "Draft two")
    monkeypatch.setattr(local_server.Handler, "client", client)
    monkeypatch.setattr(local_server.Handler, "samples", [])
    monkeypatch.setattr(local_server.Handler, "posts_dir", tmp_path)
    monkeypatch.setattr(local_server.Handler, "log_message", lambda *a: None)
    srv = local_server.make_server(port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv, client
    srv.shutdown()
    srv.server_close()


def request(srv, method, path, body=None, headers=None):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    hdrs = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    is_json = resp.getheader("Content-Type", "").startswith("application/json")
    return resp.status, dict(resp.getheaders()), json.loads(raw) if is_json and raw else raw


def test_serves_page_and_health(server):
    srv, _ = server
    status, headers, body = request(srv, "GET", "/")
    assert status == 200 and b"POST TERMINAL" in body.upper()
    status, _, body = request(srv, "GET", "/health")
    assert status == 200 and body["target"] == "local" and body["ok"] is True
    assert body["engines"] == ["local", "llm"] and "anthropic" in body["providers"]


def test_unknown_paths_and_files_are_not_served(server):
    srv, _ = server
    for path in ("/local_server.py", "/../CLAUDE.md", "/src/indo_core/drafting.py"):
        assert request(srv, "GET", path)[0] == 404


def test_full_flow_generate_revise_save_list(server, draft_request):
    srv, client = server
    status, _, gen = request(srv, "POST", "/drafts", {**draft_request, "engine": "llm"})
    assert status == 200 and gen["draft"] == "Draft one"

    status, _, rev = request(srv, "POST", "/drafts/revise", {"history": gen["history"], "feedback": "Shorter"})
    assert status == 200 and rev["draft"] == "Draft two" and len(rev["history"]) == 4

    status, _, saved = request(srv, "POST", "/posts", {"topic": draft_request["topic"], "when": "Oct", "draft": rev["draft"]})
    assert status == 201 and saved["path"].startswith("posts/")

    status, _, posts = request(srv, "GET", "/posts")
    assert status == 200 and posts[0]["draft"] == "Draft two"


def test_validation_errors_are_400_with_message(server, draft_request):
    srv, client = server
    draft_request["when"] = ""
    status, _, body = request(srv, "POST", "/drafts", draft_request)
    assert status == 400 and body["error"] == "Date is required."
    assert client.messages.calls == []


def test_non_json_body_is_rejected(server):
    srv, _ = server
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/posts", body=b"topic=x", headers={"Host": f"127.0.0.1:{port}", "Content-Type": "application/x-www-form-urlencoded"})
    resp = conn.getresponse()
    assert resp.status == 400 and "JSON" in json.loads(resp.read())["error"]


def test_foreign_host_header_is_refused(server):
    srv, _ = server
    status, _, body = request(srv, "GET", "/health", headers={"Host": "evil.example:8787"})
    assert status == 403


def test_cors_only_for_local_origins(server):
    srv, _ = server
    port = srv.server_address[1]
    _, headers, _ = request(srv, "GET", "/health", headers={"Origin": f"http://localhost:{port}"})
    assert headers.get("Access-Control-Allow-Origin") == f"http://localhost:{port}"
    _, headers, _ = request(srv, "GET", "/health", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in headers
    status, headers, _ = request(srv, "OPTIONS", "/drafts", headers={"Origin": f"http://localhost:{port}"})
    assert status == 204 and "POST" in headers["Access-Control-Allow-Methods"]


def test_model_failures_map_to_their_status(server, draft_request, fake_client, monkeypatch):
    srv, _ = server
    monkeypatch.setattr(local_server.Handler, "client", fake_client(("", "refusal")))
    status, _, body = request(srv, "POST", "/drafts", {**draft_request, "engine": "llm"})
    assert status == 422 and "declined" in body["error"]


def test_local_engine_works_without_any_client(server, draft_request):
    srv, client = server
    status, _, gen = request(srv, "POST", "/drafts", {**draft_request, "engine": "local"})
    assert status == 200 and gen["engine"]["engine"] == "local" and client.messages.calls == []
    status, _, rev = request(srv, "POST", "/drafts/revise", {"history": gen["history"], "feedback": "shorter"})
    assert status == 200 and rev["engine"]["engine"] == "local"


# ---------- Settings, profile scan ----------

def test_settings_roundtrip_masks_secrets(server):
    srv, _ = server
    status, _, body = request(srv, "POST", "/settings", {"bedrock": {"region": "us-west-2", "access_key_id": "AKIAEXAMPLE9999",
                                                                     "secret_access_key": "topsecret"}})
    assert status == 200 and body["bedrock"]["keys_saved"] and body["bedrock"]["key_hint"] == "…9999"
    status, _, body = request(srv, "GET", "/settings")
    assert status == 200 and "topsecret" not in json.dumps(body) and body["bedrock"]["region"] == "us-west-2"
    status, _, body = request(srv, "POST", "/settings", {"keys": {"bogus": "x"}})
    assert status == 400


def test_scan_fills_the_persona_from_the_public_profile(server, tmp_path, monkeypatch):
    from indo_core import linkedin
    from test_linkedin import PAGE

    srv, _ = server
    real_scan = linkedin.scan
    monkeypatch.setattr(local_server.Handler, "persona_dir", tmp_path / "persona")
    monkeypatch.setattr(local_server.linkedin, "scan", lambda url: real_scan(url, fetch=lambda u: PAGE))
    status, _, body = request(srv, "POST", "/persona/scan", {"url": "linkedin.com/in/asha-menon"})
    assert status == 200, body
    assert body["profile"]["name"] == "Asha Menon" and body["profile"]["linkedin_url"] == "https://www.linkedin.com/in/asha-menon"
    assert body["post_count"] == 1 and body["persona"]["answers"]["headline"].startswith("Cloud and AI builder")
    # Typed answers survive a rescan unless overwrite is asked for.
    request(srv, "POST", "/persona", {**body["profile"], "headline": "My own words"})
    _, _, again = request(srv, "POST", "/persona/scan", {})
    assert again["profile"]["headline"] == "My own words"
    _, _, over = request(srv, "POST", "/persona/scan", {"overwrite": True})
    assert over["profile"]["headline"].startswith("Cloud and AI builder")


def test_scan_errors_are_readable(server, monkeypatch):
    from indo_core.sources import FetchError

    srv, _ = server

    def blocked(url):
        raise FetchError("linkedIn asked for a sign-in")
    monkeypatch.setattr(local_server.linkedin, "scan", blocked)
    status, _, body = request(srv, "POST", "/persona/scan", {"url": "https://www.linkedin.com/in/x"})
    assert status == 502 and body["error"] == "LinkedIn asked for a sign-in."
