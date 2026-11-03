"""Helpers shared by the Lambda handlers (API Gateway HTTP API, payload v2)."""

import base64
import json
import logging

from indo_core import ValidationError

log = logging.getLogger()
log.setLevel(logging.INFO)

MAX_BODY = 6 * 1024 * 1024


def respond(status, data):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(data),
    }


def error(status, message):
    return respond(status, {"error": message})


def json_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    if len(raw) > MAX_BODY:
        raise ValidationError("Request body is too large.")
    try:
        return json.loads(raw or "null")
    except json.JSONDecodeError:
        raise ValidationError("Request body is not valid JSON.") from None


def user_sub(event):
    """Cognito `sub` placed in the request context by the Lambda authorizer."""
    return (event.get("requestContext", {}).get("authorizer", {}).get("lambda") or {}).get("sub")
