"""Persistent SQLite FTS5 + Vector Hybrid Storage Engine.

Zero external dependencies: uses standard library sqlite3 with FTS5 BM25
and sublinear TF-IDF n-gram vector cosine similarity.
Runs entirely on CPU in milliseconds with zero gigabyte model downloads.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

DB_DIR = Path.home() / ".local/share/linkedin-indo/vectordb"
DB_FILE = DB_DIR / "knowledge.db"

STOPWORDS = set("""
a an and are as at be been but by for from has have i in is it its me my of on or our so that the
their them this to was we were with you your will just very am about into over after before can could
should would do did does not no if each which when where who why how all any both each few more most
other some such only own same so than too s t
""".split())


def get_db_path() -> Path:
    override = os.environ.get("INDO_VECTORDB_PATH")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_FILE


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    target = path or get_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                file_path TEXT,
                category TEXT NOT NULL,
                heading TEXT,
                content TEXT NOT NULL,
                tokens_json TEXT,
                norm REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)
        """)
        # FTS5 full text search table
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                heading,
                source,
                content='chunks',
                content_rowid='rowid'
            )
        """)
        # Triggers to keep FTS in sync with chunks table
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, content, heading, source)
                VALUES (new.rowid, new.content, new.heading, new.source);
            END;
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content, heading, source)
                VALUES ('delete', old.rowid, old.content, old.heading, old.source);
            END;
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content, heading, source)
                VALUES ('delete', old.rowid, old.content, old.heading, old.source);
                INSERT INTO chunks_fts(rowid, content, heading, source)
                VALUES (new.rowid, new.content, new.heading, new.source);
            END;
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                val TEXT
            )
        """)


def tokenize(text: str) -> list[str]:
    """Tokenize text into lower-case words and bigrams, ignoring stopwords."""
    words = [w for w in re.findall(r"[a-z0-9+#]+", (text or "").lower()) if w not in STOPWORDS and len(w) > 1]
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return words + bigrams


def compute_vector(tokens: list[str]) -> tuple[dict[str, float], float]:
    """Compute sublinear TF-weighted vector and its L2 norm."""
    if not tokens:
        return {}, 1.0
    counts = Counter(tokens)
    vec = {}
    sum_sq = 0.0
    for term, count in counts.items():
        weight = 1.0 + math.log(count)
        vec[term] = round(weight, 4)
        sum_sq += weight * weight
    norm = math.sqrt(sum_sq) or 1.0
    return vec, round(norm, 4)


def cosine_similarity(query_vec: dict[str, float], query_norm: float,
                      doc_vec: dict[str, float], doc_norm: float) -> float:
    """Fast cosine similarity between query and doc sparse vectors."""
    if not query_vec or not doc_vec or query_norm <= 0 or doc_norm <= 0:
        return 0.0
    dot = 0.0
    if len(query_vec) < len(doc_vec):
        for term, q_val in query_vec.items():
            if term in doc_vec:
                dot += q_val * doc_vec[term]
    else:
        for term, d_val in doc_vec.items():
            if term in query_vec:
                dot += d_val * query_vec[term]
    return max(0.0, min(1.0, dot / (query_norm * doc_norm)))
