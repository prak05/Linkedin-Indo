import json

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from handlers import draft  # noqa: E402

PARAM = "/workshop/indo/anthropic-api-key"


@pytest.fixture
def ssm(monkeypatch, fake_client):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("API_KEY_PARAM", PARAM)
    monkeypatch.setattr(draft, "_client", None)
    seen = {}

    def get_client(provider, api_key, timeout, max_retries):
        seen.update(provider=provider, api_key=api_key, timeout=timeout, max_retries=max_retries)
        return fake_client("Cloud draft", "Cloud draft v2")

    monkeypatch.setattr(draft, "get_client", get_client)
    monkeypatch.setattr("indo_core.llm.load_samples", lambda: [])
    monkeypatch.setattr("indo_core.local_engine.load_samples", lambda: [])
    with moto.mock_aws():
        client = boto3.client("ssm")
        yield client, seen


def test_generate_and_revise_with_key_from_ssm(ssm, llm_request):
    client, seen = ssm
    client.put_parameter(Name=PARAM, Type="SecureString", Value="sk-test")
    res = draft.handler({"routeKey": "POST /drafts", "body": json.dumps(llm_request)}, None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200 and body["draft"] == "Cloud draft"
    assert seen == {"provider": "anthropic", "api_key": "sk-test", "timeout": 20.0, "max_retries": 0}

    res = draft.handler({"routeKey": "POST /drafts/revise", "body": json.dumps({"history": body["history"], "feedback": "Shorter"})}, None)
    assert res["statusCode"] == 200 and json.loads(res["body"])["draft"] == "Cloud draft v2"


def test_placeholder_key_gives_a_clear_error(ssm, llm_request):
    client, _ = ssm
    client.put_parameter(Name=PARAM, Type="SecureString", Value="REPLACE_ME")
    res = draft.handler({"routeKey": "POST /drafts", "body": json.dumps(llm_request)}, None)
    assert res["statusCode"] == 500 and "has not been set" in json.loads(res["body"])["error"]


def test_validation_runs_before_any_ssm_call(ssm, draft_request):
    draft_request["topic"] = ""
    res = draft.handler({"routeKey": "POST /drafts", "body": json.dumps(draft_request)}, None)
    # No parameter exists, so reaching SSM would have failed with 500.
    assert res["statusCode"] == 400


def test_local_engine_runs_in_lambda_without_ssm(ssm, draft_request):
    # No parameter exists, so touching SSM would fail with 500.
    res = draft.handler({"routeKey": "POST /drafts", "body": json.dumps({**draft_request, "engine": "local"})}, None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200 and body["engine"]["engine"] == "local"
    res = draft.handler({"routeKey": "POST /drafts/revise",
                         "body": json.dumps({"history": body["history"], "feedback": "shorter"})}, None)
    assert res["statusCode"] == 200


def test_cloud_rejects_providers_it_has_no_credentials_for(ssm, llm_request):
    res = draft.handler({"routeKey": "POST /drafts", "body": json.dumps({**llm_request, "provider": "openai"})}, None)
    assert res["statusCode"] == 400 and "anthropic provider" in json.loads(res["body"])["error"]
