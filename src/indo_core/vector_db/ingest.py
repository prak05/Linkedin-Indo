"""Ingestion Pipeline: reads documents across this PC and builds the SQLite + Vector DB.

Ingests:
  1. ALL_DOCUMENTS_DATA_EXPORT.md (41 MB, 2,119 documents with full extracted text)
  2. prakhar_sharma_master_cv_inventory.md
  3. Linkedin Indo resumes (*.md)
  4. Dataset persona.json & evidence.json
  5. GitHub projects (* / README.md)
  6. KSERC regulatory docs
  7. AWS / CloudConnect docs
  8. Personal profile and project files

Run standalone:
  python3.13 src/indo_core/vector_db/ingest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# Support running directly as script or as package module
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from .db import (
        compute_vector,
        get_connection,
        init_db,
        tokenize,
    )
except (ImportError, ValueError):
    from indo_core.vector_db.db import (
        compute_vector,
        get_connection,
        init_db,
        tokenize,
    )


CHUNK_WORD_LIMIT = 350
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 100


def _doc_hash(text: str, source: str) -> str:
    h = hashlib.sha256()
    h.update(source.encode("utf-8", errors="replace"))
    h.update(text[:200].encode("utf-8", errors="replace"))
    h.update(text[-200:].encode("utf-8", errors="replace"))
    h.update(str(len(text)).encode("ascii"))
    return h.hexdigest()[:20]


def chunk_text(text: str, chunk_size: int = CHUNK_WORD_LIMIT, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Splits text into overlapping word chunks."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text.strip()]

    chunks = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) >= 15:  # discard tiny fragments
            chunks.append(" ".join(chunk_words).strip())
        i += step
    return chunks


def parse_all_documents_export(export_path: Path):
    """Yields parsed document items from ALL_DOCUMENTS_DATA_EXPORT.md."""
    if not export_path.exists():
        return

    print(f"[ingest] Scanning master export: {export_path} ({export_path.stat().st_size // (1024 * 1024)} MB)...")

    # Document pattern in the export:
    # ### <num>. <title>
    # - **Category / Group:** `<group>`
    # - **File Path:** [<path>](...)
    # [content]
    doc_re = re.compile(
        r"(?:^|\n)###\s+\d+\.\s+([^\n]+)\n+"
        r"(?:-\s+\*\*Category\s*/\s*Group:\*\*\s*`([^`]+)`\n+)?"
        r"(?:-\s+\*\*File Path:\*\*\s*\[([^\]]+)\])?",
        re.MULTILINE
    )

    with open(export_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Split by ### headers
    matches = list(doc_re.finditer(content))
    print(f"[ingest] Found {len(matches)} document sections in master export.")

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        category_group = (match.group(2) or "Documents").strip()
        file_path = (match.group(3) or "").strip()

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        doc_body = content[start_pos:end_pos].strip()

        # Clean code fence wrappers ```text ... ```
        clean_text = re.sub(r"^```[a-z]*\n", "", doc_body, flags=re.MULTILINE)
        clean_text = re.sub(r"\n```$", "", clean_text, flags=re.MULTILINE).strip()

        if len(clean_text) < 30:
            continue

        yield {
            "source": title,
            "file_path": file_path,
            "category": "documents_export",
            "heading": f"{category_group}: {title}",
            "text": clean_text
        }


def parse_cv_inventory(cv_path: Path):
    """Parses prakhar_sharma_master_cv_inventory.md into sections."""
    if not cv_path.exists():
        return

    print(f"[ingest] Parsing master CV: {cv_path}")
    text = cv_path.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"\n(?=##\s+)", text)
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
        if not body:
            body = lines[0]
        yield {
            "source": f"Master CV: {heading}",
            "file_path": str(cv_path),
            "category": "profile",
            "heading": heading,
            "text": body
        }


def parse_resumes(resumes_dir: Path):
    """Parses resumes/*.md files."""
    if not resumes_dir.is_dir():
        return

    for md in sorted(resumes_dir.glob("*.md")):
        print(f"[ingest] Parsing resume: {md.name}")
        text = md.read_text(encoding="utf-8", errors="replace")
        yield {
            "source": f"Resume ({md.stem.replace('_', ' ')})",
            "file_path": str(md),
            "category": "resume",
            "heading": md.stem,
            "text": text
        }


def parse_dataset_json(dataset_dir: Path):
    """Parses persona.json, evidence.json, and other dataset files."""
    if not dataset_dir.is_dir():
        return

    for fname in ["persona.json", "evidence.json"]:
        fpath = dataset_dir / fname
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                text = json.dumps(data, indent=2)
                yield {
                    "source": f"Dataset: {fname}",
                    "file_path": str(fpath),
                    "category": "persona",
                    "heading": fname,
                    "text": text
                }
            except Exception:
                pass


def parse_github_readmes(github_dir: Path):
    """Parses all README.md files under GITHUB/."""
    if not github_dir.is_dir():
        return

    for readme in sorted(github_dir.glob("*/README.md")):
        repo_name = readme.parent.name
        try:
            text = readme.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) > 40:
                yield {
                    "source": f"GitHub: {repo_name}",
                    "file_path": str(readme),
                    "category": "github_project",
                    "heading": f"{repo_name} Project Overview",
                    "text": text
                }
        except Exception:
            pass


def parse_kserc_and_aws(home_dir: Path):
    """Parses specific text/markdown notes in KSERC and AWS."""
    # KSERC notes
    kserc = home_dir / "KSERC"
    if kserc.is_dir():
        for f in kserc.glob("*.txt"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if len(text.strip()) > 30:
                    yield {
                        "source": f"KSERC: {f.name}",
                        "file_path": str(f),
                        "category": "kserc",
                        "heading": f"KSERC Regulatory Material ({f.stem})",
                        "text": text
                    }
            except Exception:
                pass

    # AWS CloudConnect notes / documents
    aws_cc = home_dir / "AWS" / "CloudConnect"
    if aws_cc.is_dir():
        for ext in ("*.txt", "*.md", "*.odt"):
            for f in aws_cc.glob(ext):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    if len(text.strip()) > 30:
                        yield {
                            "source": f"AWS CloudConnect: {f.name}",
                            "file_path": str(f),
                            "category": "aws_event",
                            "heading": "Builder's CloudConnect Trivandrum",
                            "text": text
                        }
                except Exception:
                    pass


def build_index(force: bool = False, conn: sqlite3.Connection | None = None) -> dict:
    """Builds or refreshes the SQLite FTS5 + vector knowledge base."""
    start_time = time.time()
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    init_db(conn)

    if force:
        print("[ingest] Force flag active: clearing existing chunks...")
        with conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM chunks_fts")
            conn.execute("DELETE FROM meta")

    # Check existing IDs
    existing_ids = set()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM chunks")
    for row in cursor.fetchall():
        existing_ids.add(row[0])

    home = Path.home()
    linkedin_indo_dir = Path(__file__).resolve().parents[3]

    total_chunks = 0
    added_chunks = 0
    skipped_chunks = 0

    batch = []

    def flush_batch():
        nonlocal added_chunks, batch
        if not batch:
            return
        with conn:
            conn.executemany("""
                INSERT OR IGNORE INTO chunks
                (id, source, file_path, category, heading, content, tokens_json, norm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
        added_chunks += len(batch)
        batch = []
        print(f"  [ingest] Added {added_chunks} chunks...", end="\r", flush=True)

    # Collector pipeline
    sources = [
        parse_cv_inventory(home / "prakhar_sharma_master_cv_inventory.md"),
        parse_resumes(linkedin_indo_dir / "resumes"),
        parse_dataset_json(linkedin_indo_dir / "dataset"),
        parse_github_readmes(home / "GITHUB"),
        parse_kserc_and_aws(home),
        parse_all_documents_export(home / "ALL_DOCUMENTS_DATA_EXPORT.md"),
    ]

    for source_gen in sources:
        for item in source_gen:
            chunks = chunk_text(item["text"])
            for idx, chunk in enumerate(chunks):
                total_chunks += 1
                c_id = _doc_hash(chunk, f"{item['source']}:{idx}")
                if c_id in existing_ids:
                    skipped_chunks += 1
                    continue

                existing_ids.add(c_id)
                tokens = tokenize(f"{item['heading']} {chunk}")
                vec, norm = compute_vector(tokens)
                tokens_json = json.dumps(vec)

                batch.append((
                    c_id,
                    item["source"][:150],
                    item.get("file_path", "")[:250],
                    item.get("category", "documents_export")[:50],
                    item.get("heading", "")[:150],
                    chunk,
                    tokens_json,
                    norm
                ))

                if len(batch) >= BATCH_SIZE:
                    flush_batch()

    flush_batch()

    # Record metadata
    elapsed = round(time.time() - start_time, 2)
    stats_data = {
        "status": "ready",
        "total": len(existing_ids),
        "added": added_chunks,
        "skipped": skipped_chunks,
        "seconds": elapsed,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with conn:
        conn.execute("INSERT OR REPLACE INTO meta (key, val) VALUES ('stats', ?)", (json.dumps(stats_data),))

    print(f"\n[ingest] Complete! Total: {len(existing_ids):,} chunks (Added: {added_chunks:,}, Skipped: {skipped_chunks:,}) in {elapsed}s.")

    if close_after:
        conn.close()

    return stats_data


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    build_index(force=force_run)
