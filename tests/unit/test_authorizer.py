import time

import pytest

jwt = pytest.importorskip("jwt")
rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")

from handlers import authorizer  # noqa: E402

REGION, POOL, CLIENT = "us-west-2", "us-west-2_TEST", "client-123"
ISS = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}"


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("AWS_REGION", REGION)
    monkeypatch.setenv("USER_POOL_ID", POOL)
    monkeypatch.setenv("APP_CLIENT_ID", CLIENT)
    good = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": good.public_key()})()

    monkeypatch.setattr(authorizer, "_jwks", FakeJwks())
    return good, other


def token(key, **overrides):
    now = int(time.time())
    claims = {"sub": "user-1", "iss": ISS, "aud": CLIENT, "token_use": "id", "iat": now, "exp": now + 600, **overrides}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def call(value):
    return authorizer.handler({"headers": {"authorization": value} if value is not None else {}}, None)


def test_valid_id_token_is_authorized_with_sub(keys):
    good, _ = keys
    assert call(token(good)) == {"isAuthorized": True, "context": {"sub": "user-1"}}
    assert call("Bearer " + token(good))["isAuthorized"] is True


@pytest.mark.parametrize("overrides", [
    {"aud": "someone-else"},
    {"iss": "https://evil.example"},
    {"token_use": "access"},
    {"exp": int(time.time()) - 10},
])
def test_wrong_claims_are_rejected(keys, overrides):
    good, _ = keys
    assert call(token(good, **overrides)) == {"isAuthorized": False}


def test_wrong_signature_missing_and_garbage_are_rejected(keys):
    _, other = keys
    assert call(token(other)) == {"isAuthorized": False}
    assert call(None) == {"isAuthorized": False}
    assert call("not-a-jwt") == {"isAuthorized": False}


def test_unsigned_token_is_rejected(keys):
    unsigned = jwt.encode({"sub": "x", "iss": ISS, "aud": CLIENT, "token_use": "id",
                           "iat": int(time.time()), "exp": int(time.time()) + 600}, None, algorithm="none")
    assert call(unsigned) == {"isAuthorized": False}
