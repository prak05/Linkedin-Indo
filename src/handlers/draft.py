"""POST /drafts and POST /drafts/revise.

Engines on the cloud backend: "local" (the offline model, runs inside Lambda) and
"llm" with provider "anthropic" (key read from SSM).
"""

import os

import boto3

import indo_core
from indo_core.llm import get_client

from .common import error, json_body, log, respond

CLOUD_PROVIDERS = {"anthropic"}
_client = None


def _anthropic():
    """Read the API key from SSM once per container; never log it."""
    global _client
    if _client is None:
        ssm = boto3.client("ssm")
        key = ssm.get_parameter(Name=os.environ["API_KEY_PARAM"], WithDecryption=True)["Parameter"]["Value"]
        if not key or key == "REPLACE_ME":
            raise indo_core.DraftError("The Anthropic API key has not been set in SSM yet.", 500)
        _client = get_client("anthropic", api_key=key, timeout=20.0, max_retries=0)
    return _client


def _client_for(body, revising=False):
    choice = indo_core.engine_choice(body if not revising else {**body, "engine": body.get("engine") or "llm"})
    if choice["engine"] == "local":
        return None
    if choice["provider"] not in CLOUD_PROVIDERS:
        raise indo_core.ValidationError("The cloud backend supports the local engine and the anthropic provider.")
    return _anthropic()


def handler(event, context):
    route = event.get("routeKey")
    try:
        body = json_body(event)
        # Validate before touching SSM, so bad input is a cheap 400.
        if route == "POST /drafts":
            indo_core.validate_draft_request(body)
            return respond(200, indo_core.generate(body, client=_client_for(body)))
        if route == "POST /drafts/revise":
            indo_core.validate_revise_request(body)
            if indo_core.drafting.made_locally(body["history"]):
                return respond(200, indo_core.revise(body))
            return respond(200, indo_core.revise(body, client=_client_for(body, revising=True)))
        if route == "POST /cover-letters":
            req = indo_core.cover_letters.validate_request(body)
            return respond(200, {"draft": indo_core.cover_letters.generate(req), "engine": "cloud"})
        if route == "POST /cover-letters/revise":
            return respond(200, {**indo_core.cover_letters.revise(body), "engine": "cloud"})
        return error(404, "Not found.")
    except indo_core.ValidationError as e:
        return error(400, str(e))
    except indo_core.DraftError as e:
        log.warning("draft failed on %s: status %s", route, e.status)
        return error(e.status, str(e))
    except Exception:
        log.exception("unhandled error on %s", route)
        return error(500, "Something went wrong on the cloud backend.")
