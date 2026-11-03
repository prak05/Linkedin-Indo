import json

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from handlers import posts  # noqa: E402


def event(route, sub="user-1", body=None):
    ev = {"routeKey": route, "requestContext": {"authorizer": {"lambda": {"sub": sub} if sub else None}}}
    if body is not None:
        ev["body"] = json.dumps(body)
    return ev


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("TABLE_NAME", "workshop-indo-posts")
    with moto.mock_aws():
        ddb = boto3.resource("dynamodb")
        ddb.create_table(
            TableName="workshop-indo-posts", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "user_sub", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "user_sub", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
        )
        monkeypatch.setattr(posts, "_table", None)
        yield


def test_health_needs_no_auth():
    res = posts.handler(event("GET /health", sub=None), None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200 and body["target"] == "cloud" and body["ok"] is True
    assert body["engines"] == ["local", "llm"] and list(body["providers"]) == ["anthropic"]


def test_save_and_list_are_scoped_to_the_caller(table):
    a = posts.handler(event("POST /posts", body={"topic": "Hackathon", "when": "Oct", "draft": "Mine"}), None)
    assert a["statusCode"] == 201 and len(json.loads(a["body"])["id"]) == 32
    posts.handler(event("POST /posts", sub="user-2", body={"topic": "Other", "when": "Nov", "draft": "Theirs"}), None)

    res = posts.handler(event("GET /posts"), None)
    items = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert [i["draft"] for i in items] == ["Mine"]
    assert set(items[0]) == {"id", "topic", "when", "created_at", "draft"}


def test_invalid_body_is_400(table):
    res = posts.handler(event("POST /posts", body={"topic": "T"}), None)
    assert res["statusCode"] == 400 and "Date is required" in json.loads(res["body"])["error"]
    res = posts.handler({**event("POST /posts"), "body": "{not json"}, None)
    assert res["statusCode"] == 400


def test_missing_authorizer_context_is_401(table):
    assert posts.handler(event("GET /posts", sub=None), None)["statusCode"] == 401
