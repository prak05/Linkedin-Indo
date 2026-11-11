"""Local-first cover-letter generation for job applications."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .validation import ValidationError, _text

TRACKS = ("software_ai_cloud", "management_hr", "all_rounder")
MAX_JOB_DESCRIPTION = 12000


def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    track = payload.get("track", "all_rounder")
    if track not in TRACKS:
        raise ValidationError(f"track must be one of: {', '.join(TRACKS)}.")
    return {
        "track": track,
        "job_title": _text(payload.get("job_title"), "Job title", max_len=200),
        "company": _text(payload.get("company"), "Company", max_len=200),
        "job_description": _text(payload.get("job_description"), "Job description",
                                  required=False, max_len=MAX_JOB_DESCRIPTION) or "",
        "location": _text(payload.get("location"), "Location", required=False, max_len=200) or "",
    }


def _name(persona):
    return ((persona or {}).get("answers") or {}).get("name") or "Prakhar Sharma"


def _keywords(text):
    known = (
        "Python", "Java", "JavaScript", "SQL", "AWS", "Google Cloud", "IBM Cloud",
        "Terraform", "Docker", "FastAPI", "RAG", "machine learning", "Kubernetes",
        "React", "Android", "JDBC", "data science", "event management", "leadership",
        "stakeholder", "community", "HR", "recruiting", "project management",
    )
    lower = text.lower()
    return [word for word in known if word.lower() in lower][:8]


def generate(payload, persona=None):
    req = validate_request(payload)
    name = _name(persona)
    jd_keys = _keywords(req["job_description"])
    track = req["track"]
    if track == "software_ai_cloud":
        proof = (
            "My strongest fit is the combination of applied engineering and cloud delivery: "
            "I have contributed to KSERC regulatory automation, built LinkedIn Indo as a "
            "local-first drafting tool with AWS-capable infrastructure, and worked on "
            "RAG, document processing, machine learning, REST services, and cloud workflows."
        )
        contribution = (
            "I would bring a practical, evidence-first approach to backend services, "
            "AI evaluation, cloud infrastructure, and developer-facing products."
        )
    elif track == "management_hr":
        proof = (
            "Alongside my technical background, I have built student communities, hosted "
            "the AWS Student Builder Group exposure talk show, organised GitHub Geeks and "
            "Data Manipulators workshops through Vidya Sadhnam, and coordinated speakers, "
            "audiences, partners, candidate profiles, HR communication, and event logistics."
        )
        contribution = (
            "I would bring structured execution, clear communication, technical fluency, "
            "and a people-first approach to programs, operations, recruiting, or community work."
        )
    else:
        proof = (
            "My experience spans software development, AI and cloud projects, data science, "
            "Android, technical writing, community leadership, and public event execution. "
            "I have built projects including LinkedIn Indo, KSERC, MediScribe, agricultural "
            "ML systems, a JDBC banking system, and Report Indo."
        )
        contribution = (
            "I would bring adaptability, ownership, concise communication, and the ability "
            "to move between technical delivery and stakeholder-facing work."
        )
    alignment = (
        f"The role's focus on {', '.join(jd_keys)} is especially relevant to my background."
        if jd_keys else
        "The role's focus is closely aligned with my current direction in technology and applied problem-solving."
    )
    location = f" in {req['location']}" if req["location"] else ""
    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to apply for the {req['job_title']} position at {req['company']}{location}. "
        f"I am a Computer Science and Engineering student at Rajadhani Institute of Engineering "
        f"and Technology, expected to graduate in 2027, and I am seeking an opportunity to "
        f"contribute to a high-quality team while continuing to grow as an engineer and professional.\n\n"
        f"{alignment}\n\n"
        f"{proof}\n\n"
        f"{contribution}\n\n"
        f"I would welcome the opportunity to discuss how my background could support {req['company']}'s "
        f"work. Thank you for your time and consideration.\n\n"
        f"Sincerely,\n{name}\n+91 7994454919 | praksediting5@gmail.com\n"
    )


def revise(payload, persona=None):
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    request = validate_request(payload)
    feedback = _text(payload.get("feedback"), "Feedback", max_len=2000).lower()
    draft = _text(payload.get("draft"), "Draft", max_len=20000)
    if "short" in feedback:
        paragraphs = draft.split("\n\n")
        draft = "\n\n".join(paragraphs[:4] + paragraphs[-2:])
    if "formal" in feedback:
        draft = draft.replace("I am writing to apply", "I am pleased to submit my application for")
    if "technical" in feedback:
        request["track"] = "software_ai_cloud"
        draft = generate(request, persona)
    elif "management" in feedback or "hr" in feedback or "community" in feedback:
        request["track"] = "management_hr"
        draft = generate(request, persona)
    elif "all-rounder" in feedback or "balanced" in feedback:
        request["track"] = "all_rounder"
        draft = generate(request, persona)
    return {"draft": draft, "notes": [f"Applied cover-letter revision: {feedback}."]}


def save(payload, directory=None):
    req = validate_request(payload)
    draft = _text(payload.get("draft"), "Draft", max_len=20000)
    folder = Path(directory or Path(__file__).resolve().parents[2] / "cover-letters")
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{req['company']}-{req['job_title']}".lower()).strip("-")[:60]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = folder / f"{stamp}-{slug or 'application'}.md"
    path.write_text(
        "---\n"
        f"job_title: {req['job_title']}\ncompany: {req['company']}\ntrack: {req['track']}\n"
        f"created_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        "---\n\n" + draft + "\n", encoding="utf-8"
    )
    return {"id": path.stem, "path": str(path.relative_to(folder.parent))}
