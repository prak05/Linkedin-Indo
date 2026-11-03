"""POST /posts, GET /posts (per user, DynamoDB) and GET /health."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

import indo_core

from .common import error, json_body, log, respond, user_sub

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def save(sub, payload):
    post = indo_core.validate_post(payload)
    post_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    table().put_item(Item={"user_sub": sub, "sk": f"{created}#{post_id}", "id": post_id, "created_at": created, **post})
    return {"id": post_id}


def list_for(sub):
    res = table().query(KeyConditionExpression=Key("user_sub").eq(sub), ScanIndexForward=False, Limit=50)
    fields = ("id", "topic", "when", "created_at", "draft")
    return [{f: item.get(f, "") for f in fields} for item in res["Items"]]


def handler(event, context):
    route = event.get("routeKey")
    if route == "GET /health":
        # The cloud draft function offers the local engine and Claude via the Anthropic API.
        anthropic = indo_core.llm.providers()["anthropic"]
        return respond(200, {"target": "cloud", "ok": True, "engines": ["local", "llm"],
                             "providers": {"anthropic": {**anthropic, "ready": True}}})
    sub = user_sub(event)
    if not sub:
        return error(401, "Sign in first.")
    try:
        if route == "POST /posts":
            return respond(201, save(sub, json_body(event)))
        if route == "GET /posts":
            return respond(200, list_for(sub))
        return error(404, "Not found.")
    except indo_core.ValidationError as e:
        return error(400, str(e))
    except Exception:
        log.exception("unhandled error on %s", route)
        return error(500, "Something went wrong on the cloud backend.")
