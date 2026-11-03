"""Local draft storage: timestamped Markdown files in posts/ (FR-9)."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .validation import validate_post

DEFAULT_POSTS_DIR = Path(__file__).resolve().parents[2] / "posts"


def posts_dir(directory=None):
    return Path(directory or os.environ.get("INDO_POSTS_DIR") or DEFAULT_POSTS_DIR)


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "post"


def _one_line(text):
    return " ".join(text.split())


def save_post(payload, directory=None, now=None):
    """Save a draft. Returns {"id", "path"}."""
    post = validate_post(payload)
    now = now or datetime.now(timezone.utc)
    folder = posts_dir(directory)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{now:%Y%m%d-%H%M%S}-{_slug(post['topic'])}"
    path = folder / f"{stem}.md"
    n = 1
    while path.exists():
        n += 1
        path = folder / f"{stem}-{n}.md"
    path.write_text(
        "---\n"
        f"topic: {_one_line(post['topic'])}\n"
        f"when: {_one_line(post['when'])}\n"
        f"created_at: {now.isoformat(timespec='seconds')}\n"
        "---\n\n"
        f"{post['draft']}\n",
        encoding="utf-8",
    )
    return {"id": path.stem, "path": f"posts/{path.name}"}


def list_posts(directory=None):
    """Newest first: [{"id", "topic", "when", "created_at", "draft"}]."""
    folder = posts_dir(directory)
    if not folder.is_dir():
        return []
    items = []
    for path in sorted(folder.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = {}, text
        if text.startswith("---\n") and "\n---\n" in text[4:]:
            header, body = text[4:].split("\n---\n", 1)
            for line in header.splitlines():
                key, _, value = line.partition(": ")
                meta[key] = value
        items.append({"id": path.stem, "topic": meta.get("topic", ""), "when": meta.get("when", ""),
                      "created_at": meta.get("created_at", ""), "draft": body.strip()})
    return items
