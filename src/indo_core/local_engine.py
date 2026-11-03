"""LOCAL engine: draft and revise posts offline with the local model (ml.py, writer.py).

Same contract as drafting.generate/revise: returns {"draft", "history", "notes"}
and stays stateless. The first history message holds the analysis as a JSON string
with "engine": "local"; later user messages are revision requests, replayed in
order on every revision.
History is plain JSON, so the web page can send it back unchanged.
"""

import json

from . import ml, writer
from .persona import credit_line, structure, with_credit
from .prompt import load_samples
from .sources import build_source, extract_text
from .validation import ValidationError, validate_draft_request, validate_revise_request

ENGINE = "local"
STATE_VERSION = 1


def _event_text(source, fetch):
    """Text of the event material; PDFs and images are read with local tools."""
    blocks, text, notes = build_source(source, **({"fetch": fetch} if fetch else {}))
    for block in blocks:
        extracted, problem = extract_text(block["type"], block["source"]["data"])
        name = source.get("name", "the upload")
        if extracted is None:
            notes.append(f"Could not read {name}: {problem}. The draft uses only your answers.")
        else:
            notes.append(f"Read {len(extracted):,} characters from {name}.")
            text = extracted
    return text, notes


def voice_for(samples, persona=None, inspiration=None):
    """Your persona's voice (or the samples/ statistics), with a liked post's structure on top."""
    voice = dict(persona["voice"]) if persona else ml.voice_profile(samples)
    if inspiration:
        shape = structure(inspiration["text"])["pattern"]
        voice.update(hook=shape["hook"], bullets=shape["list"], short_lines=shape["short_lines"], cta=shape["cta"])
        # Length, emoji and hashtags stay yours.
    return voice


def generate(payload, samples=None, fetch=None, persona=None, inspiration=None):
    """POST /drafts. Returns {"draft", "history", "notes"}."""
    req = validate_draft_request(payload)
    event_text, notes = _event_text(req["source"], fetch)
    if persona is None:
        samples = load_samples() if samples is None else samples
        if not samples:
            notes.append("No persona yet, so the draft uses a neutral voice. Set up your persona to make it sound like you.")
    analysis = ml.analyse(req["topic"], event_text, req.get("post_text"))
    state = {"engine": ENGINE, "version": STATE_VERSION, "activity": req["activity"], "topic": req["topic"], "when": req["when"],
             "people": req["people"], "analysis": analysis, "voice": voice_for(samples, persona, inspiration),
             "credit": credit_line(inspiration)}
    found = [k for k in ("event", "rank", "prize", "organiser", "team") if analysis["facts"][k]]
    detected = f"Detected: {ml.label_name(analysis['category'])} ({analysis['confidence']:.0%} confident)."
    notes.insert(0, detected + (f" Found: {', '.join(found)}." if found else ""))
    settings, _ = writer.settings(state["voice"], [])
    draft = with_credit(writer.compose(state, settings), state["credit"])
    history = [{"role": "user", "content": json.dumps(state)}, {"role": "assistant", "content": draft}]
    return {"draft": draft, "history": history, "notes": notes}


def _text(content):
    return content if isinstance(content, str) else "".join(b.get("text", "") for b in content)


def _state(first):
    try:
        state = json.loads(_text(first["content"]))
    except json.JSONDecodeError:
        state = None
    if not isinstance(state, dict) or state.get("engine") != ENGINE or state.get("version") != STATE_VERSION:
        raise ValidationError("This draft was not made by the local engine. Start a new draft.")
    return state


def revise(payload, samples=None):
    """POST /drafts/revise. Returns {"draft", "history", "notes"}.

    `samples` is accepted for parity with drafting.revise; the voice profile was
    fixed when the draft was generated.
    """
    req = validate_revise_request(payload)
    state = _state(req["history"][0])
    feedback = [_text(m["content"]) for m in req["history"][2::2]] + [req["feedback"]]
    try:
        settings, applied = writer.settings(state["voice"], feedback)
        draft = with_credit(writer.compose(state, settings), state.get("credit"))
    except (KeyError, TypeError, ValueError, IndexError):
        raise ValidationError("The draft history is damaged. Start a new draft.") from None
    notes = [f"Applied: {', '.join(applied)}."] if applied else [f"Did not recognise that change. {writer.FEEDBACK_HELP}"]
    history = req["history"] + [{"role": "user", "content": req["feedback"]}, {"role": "assistant", "content": draft}]
    return {"draft": draft, "history": history, "notes": notes}
