import base64

import pytest

from indo_core.validation import (
    MAX_FILE_BYTES,
    ValidationError,
    validate_draft_request,
    validate_post,
    validate_revise_request,
)


def test_valid_post_request_is_cleaned(draft_request):
    draft_request["topic"] = "  Hackathon  "
    req = validate_draft_request(draft_request)
    assert req["topic"] == "Hackathon"
    assert req["people"][0] == {"name": "Asha Menon", "url": "https://www.linkedin.com/in/asha", "bio": "Mentor", "reason": None}
    assert "post_text" not in req


@pytest.mark.parametrize("field, value, message", [
    ("activity", "tweet", "activity"),
    ("topic", "", "Topic is required"),
    ("topic", "   ", "Topic is required"),
    ("topic", 42, "must be text"),
    ("when", None, "Date is required"),
    ("topic", "x" * 2001, "too long"),
])
def test_bad_fields_are_rejected(draft_request, field, value, message):
    draft_request[field] = value
    with pytest.raises(ValidationError, match=message):
        validate_draft_request(draft_request)


def test_comment_requires_pasted_post(draft_request):
    draft_request["activity"] = "comment"
    with pytest.raises(ValidationError, match="replying to"):
        validate_draft_request(draft_request)
    draft_request["post_text"] = "Great event!"
    assert validate_draft_request(draft_request)["post_text"] == "Great event!"


@pytest.mark.parametrize("source, message", [
    ({"type": "url", "url": "ftp://example.com"}, "http"),
    ({"type": "url", "url": "example.com"}, "http"),
    ({"type": "file", "media_type": "application/zip", "data": "AA=="}, ".txt, .md or .pdf"),
    ({"type": "image", "media_type": "image/bmp", "data": "AA=="}, "PNG"),
    ({"type": "image", "media_type": "image/png", "data": "not base64!"}, "base64"),
    ({"type": "file", "media_type": "text/plain"}, "no content"),
    ({"type": "video"}, "source.type"),
])
def test_bad_sources_are_rejected(draft_request, source, message):
    draft_request["source"] = source
    with pytest.raises(ValidationError, match=message):
        validate_draft_request(draft_request)


def test_oversized_file_is_rejected(draft_request):
    data = base64.b64encode(b"\0" * (MAX_FILE_BYTES + 1)).decode()
    draft_request["source"] = {"type": "file", "name": "a.pdf", "media_type": "application/pdf", "data": data}
    with pytest.raises(ValidationError, match="4 MB"):
        validate_draft_request(draft_request)


def test_person_needs_a_name_and_valid_url(draft_request):
    draft_request["people"] = [{"name": "", "url": None}]
    with pytest.raises(ValidationError, match="Person 1 name"):
        validate_draft_request(draft_request)
    draft_request["people"] = [{"name": "A", "url": "javascript:alert(1)"}]
    with pytest.raises(ValidationError, match="LinkedIn URL"):
        validate_draft_request(draft_request)


def test_revise_history_must_alternate_and_end_with_assistant():
    good = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}, {"role": "assistant", "content": "draft"}]
    assert validate_revise_request({"history": good, "feedback": "shorter"})["feedback"] == "shorter"
    with pytest.raises(ValidationError, match="assistant"):
        validate_revise_request({"history": good[:1], "feedback": "x"})
    with pytest.raises(ValidationError, match="user message"):
        validate_revise_request({"history": list(reversed(good)), "feedback": "x"})
    bad_block = [{"role": "user", "content": [{"type": "tool_use"}]}, good[1]]
    with pytest.raises(ValidationError, match="unsupported"):
        validate_revise_request({"history": bad_block, "feedback": "x"})
    with pytest.raises(ValidationError, match="Feedback"):
        validate_revise_request({"history": good, "feedback": ""})


def test_post_payload_matches_readme_contract():
    assert validate_post({"topic": "T", "when": "W", "draft": "D", "extra": 1}) == {"topic": "T", "when": "W", "draft": "D"}
    with pytest.raises(ValidationError, match="Draft"):
        validate_post({"topic": "T", "when": "W"})
