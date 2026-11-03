"""Request validation shared by every entry point (FR-10).

Inputs arrive from a browser or a terminal, so every field is checked for type,
presence and size before anything is sent to the model.
"""

import base64
import binascii
from urllib.parse import urlparse

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TEXT_CHARS = 20_000
TEXT_MEDIA_TYPES = {"text/plain", "text/markdown"}
DOC_MEDIA_TYPES = TEXT_MEDIA_TYPES | {"application/pdf"}
IMAGE_MEDIA_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_PEOPLE = 20
MAX_HISTORY = 60


class ValidationError(ValueError):
    """Bad input. The message is safe to show to the user."""


def _text(value, field, *, required=True, max_len=2000):
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{field} is required.")
    if len(value) > max_len:
        raise ValidationError(f"{field} is too long ({len(value)} characters, limit {max_len}).")
    return value or None


def http_url(value, field):
    url = _text(value, field, max_len=2000)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError(f"{field} must be a full http:// or https:// address.")
    return url


def _base64(value, field):
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field} is missing its file data.")
    # Encoded size is about 4/3 of the raw size; reject early before decoding.
    if len(value) > MAX_FILE_BYTES * 4 // 3 + 4:
        raise ValidationError("The file is larger than 4 MB.")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError(f"{field} is not valid base64 data.") from None
    if len(raw) > MAX_FILE_BYTES:
        raise ValidationError("The file is larger than 4 MB.")
    return value


def validate_source(source):
    if source is None:
        return {"type": "skip"}
    if not isinstance(source, dict):
        raise ValidationError("source must be an object.")
    kind = source.get("type", "skip")
    if kind == "skip":
        return {"type": "skip"}
    if kind == "url":
        return {"type": "url", "url": http_url(source.get("url"), "Event URL")}
    name = _text(source.get("name"), "File name", required=False, max_len=255) or "upload"
    media_type = source.get("media_type")
    if kind == "file":
        if media_type not in DOC_MEDIA_TYPES:
            raise ValidationError("Event files must be .txt, .md or .pdf.")
        if media_type in TEXT_MEDIA_TYPES:
            text = source.get("text")
            if not isinstance(text, str):
                raise ValidationError("The text file has no content.")
            if len(text.encode("utf-8")) > MAX_FILE_BYTES:
                raise ValidationError("The file is larger than 4 MB.")
            return {"type": "file", "name": name, "media_type": media_type, "text": text}
        return {"type": "file", "name": name, "media_type": media_type, "data": _base64(source.get("data"), "PDF")}
    if kind == "image":
        if media_type not in IMAGE_MEDIA_TYPES:
            raise ValidationError("Images must be PNG, JPEG, GIF or WebP.")
        return {"type": "image", "name": name, "media_type": media_type, "data": _base64(source.get("data"), "Image")}
    raise ValidationError("source.type must be one of: skip, url, file, image.")


def validate_people(people):
    if people is None:
        return []
    if not isinstance(people, list):
        raise ValidationError("people must be a list.")
    if len(people) > MAX_PEOPLE:
        raise ValidationError(f"Tag at most {MAX_PEOPLE} people.")
    out = []
    for i, person in enumerate(people, 1):
        if not isinstance(person, dict):
            raise ValidationError(f"Person {i} must be an object.")
        url = person.get("url")
        out.append({
            "name": _text(person.get("name"), f"Person {i} name", max_len=200),
            "url": http_url(url, f"Person {i} LinkedIn URL") if url else None,
            "bio": _text(person.get("bio"), f"Person {i} bio", required=False, max_len=5000),
            # Why you are tagging them: mentor, teammate, organiser, ... or your own words.
            "reason": _text(person.get("reason"), f"Why you are tagging person {i}", required=False, max_len=200),
        })
    return out


def validate_draft_request(payload):
    """Validate POST /drafts. Returns a cleaned copy."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    activity = payload.get("activity", "post")
    if activity not in ("post", "comment"):
        raise ValidationError("activity must be 'post' or 'comment'.")
    req = {
        "activity": activity,
        "topic": _text(payload.get("topic"), "Topic"),
        "when": _text(payload.get("when"), "Date", max_len=200),
        "source": validate_source(payload.get("source")),
        "people": validate_people(payload.get("people")),
    }
    if activity == "comment":
        req["post_text"] = _text(payload.get("post_text"), "The post you are replying to", max_len=MAX_TEXT_CHARS)
    return req


_ALLOWED_BLOCKS = {"text", "image", "document"}


def validate_history(history):
    if not isinstance(history, list) or not history:
        raise ValidationError("history is missing. Generate a draft first.")
    if len(history) > MAX_HISTORY:
        raise ValidationError("This draft has been revised too many times. Start a new draft.")
    expected = "user"
    for i, msg in enumerate(history):
        if not isinstance(msg, dict) or msg.get("role") != expected:
            raise ValidationError(f"history[{i}] must be a {expected} message.")
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") not in _ALLOWED_BLOCKS:
                    raise ValidationError(f"history[{i}] contains an unsupported content block.")
        elif not isinstance(content, str):
            raise ValidationError(f"history[{i}].content must be text or content blocks.")
        expected = "assistant" if expected == "user" else "user"
    if history[-1]["role"] != "assistant":
        raise ValidationError("history must end with the assistant's draft.")
    return history


def validate_revise_request(payload):
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    return {
        "history": validate_history(payload.get("history")),
        "feedback": _text(payload.get("feedback"), "Feedback", max_len=4000),
    }


def validate_post(payload):
    """Validate POST /posts (README contract: topic, when, draft)."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    return {
        "topic": _text(payload.get("topic"), "Topic"),
        "when": _text(payload.get("when"), "Date", max_len=200),
        "draft": _text(payload.get("draft"), "Draft", max_len=20_000),
    }
