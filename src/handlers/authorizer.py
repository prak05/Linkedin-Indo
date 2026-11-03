"""Lambda authorizer: accept only valid Cognito ID tokens (HTTP API, simple responses)."""

import os

import jwt

from .common import log

_jwks = None


def _issuer():
    return f"https://cognito-idp.{os.environ['AWS_REGION']}.amazonaws.com/{os.environ['USER_POOL_ID']}"


def _jwks_client():
    global _jwks
    if _jwks is None:
        _jwks = jwt.PyJWKClient(f"{_issuer()}/.well-known/jwks.json", cache_keys=True, timeout=5)
    return _jwks


def verify(token):
    """Return the token's claims, or raise jwt.PyJWTError."""
    key = _jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token, key.key, algorithms=["RS256"], audience=os.environ["APP_CLIENT_ID"], issuer=_issuer(),
        options={"require": ["exp", "iat", "sub", "token_use"]},
    )
    if claims["token_use"] != "id":
        raise jwt.InvalidTokenError("not an ID token")
    return claims


def handler(event, context):
    header = (event.get("headers") or {}).get("authorization", "")
    token = header.removeprefix("Bearer ").strip()
    if not token:
        return {"isAuthorized": False}
    try:
        claims = verify(token)
    except jwt.PyJWTError as e:
        log.info("rejected token: %s", type(e).__name__)
        return {"isAuthorized": False}
    return {"isAuthorized": True, "context": {"sub": claims["sub"]}}
