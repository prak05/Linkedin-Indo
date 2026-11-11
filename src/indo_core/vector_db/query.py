"""Hybrid Semantic + BM25 Query Engine for LinkedIn Indo Knowledge Base.

Returns cited, Perplexity-style results with source, category, match percentage,
and contextual excerpts.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from .db import (
        compute_vector,
        cosine_similarity,
        get_connection,
        tokenize,
    )
except (ImportError, ValueError):
    from indo_core.vector_db.db import (
        compute_vector,
        cosine_similarity,
        get_connection,
        tokenize,
    )



def _sanitize_fts_query(query: str) -> str:
    """Sanitize user query for SQLite FTS5."""
    clean = re.sub(r"[^\w\s]", " ", query)
    tokens = clean.strip().split()
    if not tokens:
        return ""
    # Use OR with prefix matching for high recall
    return " OR ".join(f'"{t}"*' for t in tokens if len(t) > 1) or '""'


def search(
    query: str,
    n_results: int = 8,
    category_filter: str | None = None,
    conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Hybrid search across the indexed knowledge base.

    Returns:
        List of dicts:
            {
                "rank": int,
                "source": str,
                "file_path": str,
                "category": str,
                "heading": str,
                "score": float (0.0 to 1.0),
                "excerpt": str,
                "content": str
            }
    """
    query = (query or "").strip()
    if not query:
        return []

    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        q_tokens = tokenize(query)
        q_vec, q_norm = compute_vector(q_tokens)
        fts_expr = _sanitize_fts_query(query)

        candidates: dict[str, dict[str, Any]] = {}

        # 1. Full-Text Search via FTS5 BM25
        if fts_expr:
            sql = """
                SELECT
                    c.id, c.source, c.file_path, c.category, c.heading, c.content,
                    c.tokens_json, c.norm,
                    bm25(chunks_fts, 10.0, 5.0, 1.0) AS bm25_rank
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.rowid = c.rowid
                WHERE chunks_fts MATCH ?
            """
            params: list[Any] = [fts_expr]
            if category_filter:
                sql += " AND c.category = ?"
                params.append(category_filter)

            sql += " ORDER BY bm25_rank ASC LIMIT ?"
            params.append(max(n_results * 5, 40))

            try:
                for row in conn.execute(sql, params).fetchall():
                    # In SQLite FTS5, lower bm25() score is better (it's negative).
                    # Normalize bm25 to a 0..1 scale
                    bm25_raw = float(row["bm25_rank"])
                    bm25_score = 1.0 / (1.0 + max(0.0, abs(bm25_raw) / 10.0))

                    candidates[row["id"]] = {
                        "id": row["id"],
                        "source": row["source"],
                        "file_path": row["file_path"],
                        "category": row["category"],
                        "heading": row["heading"],
                        "content": row["content"],
                        "tokens_json": row["tokens_json"],
                        "norm": float(row["norm"] or 1.0),
                        "bm25_score": bm25_score,
                    }
            except sqlite3.OperationalError:
                # In case FTS table isn't populated yet or match syntax error
                pass

        # 2. Vector Cosine Similarity Fallback / Augment
        # If FTS returned few results, pull top candidates by keyword overlap
        if len(candidates) < n_results * 2:
            like_clauses = []
            like_params = []
            for t in q_tokens[:4]:
                if len(t) > 3 and "_" not in t:
                    like_clauses.append("content LIKE ?")
                    like_params.append(f"%{t}%")

            if like_clauses:
                sql_like = f"SELECT id, source, file_path, category, heading, content, tokens_json, norm FROM chunks WHERE ({' OR '.join(like_clauses)})"
                if category_filter:
                    sql_like += " AND category = ?"
                    like_params.append(category_filter)
                sql_like += " LIMIT 50"

                for row in conn.execute(sql_like, like_params).fetchall():
                    if row["id"] not in candidates:
                        candidates[row["id"]] = {
                            "id": row["id"],
                            "source": row["source"],
                            "file_path": row["file_path"],
                            "category": row["category"],
                            "heading": row["heading"],
                            "content": row["content"],
                            "tokens_json": row["tokens_json"],
                            "norm": float(row["norm"] or 1.0),
                            "bm25_score": 0.2,
                        }

        # 3. Hybrid Scoring & Reranking
        scored_list = []
        for cand in candidates.values():
            try:
                doc_vec = json.loads(cand["tokens_json"]) if cand["tokens_json"] else {}
            except Exception:
                doc_vec = {}

            cos_sim = cosine_similarity(q_vec, q_norm, doc_vec, cand["norm"])
            bm25 = cand.get("bm25_score", 0.0)

            # Combined hybrid score: 60% cosine semantic match + 40% keyword match
            hybrid_score = round(0.6 * cos_sim + 0.4 * bm25, 4)

            # Boost exact title/source matches
            q_lower = query.lower()
            if q_lower in (cand["source"] or "").lower() or q_lower in (cand["heading"] or "").lower():
                hybrid_score = min(1.0, hybrid_score + 0.25)

            # Clean excerpt
            content_clean = " ".join((cand["content"] or "").split())
            excerpt = content_clean[:320].strip()
            if len(content_clean) > 320:
                excerpt += "..."

            scored_list.append({
                "source": cand["source"],
                "file_path": cand["file_path"],
                "category": cand["category"],
                "heading": cand["heading"],
                "score": hybrid_score,
                "excerpt": excerpt,
                "content": cand["content"]
            })

        # Sort descending by hybrid score
        scored_list.sort(key=lambda x: -x["score"])

        results = []
        for idx, item in enumerate(scored_list[:n_results], 1):
            item["rank"] = idx
            results.append(item)

        return results

    finally:
        if close_after and conn:
            conn.close()


def stats(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Returns knowledge base index statistics."""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM chunks")
        total = cur.fetchone()[0]

        cur.execute("SELECT val FROM meta WHERE key = 'stats'")
        row = cur.fetchone()
        stored_stats = json.loads(row[0]) if row else {}

        return {
            "status": "ready" if total > 0 else "empty",
            "total": total,
            "seconds": stored_stats.get("seconds", 0),
            "last_updated": stored_stats.get("last_updated", "never"),
            "db_path": str(conn.execute("PRAGMA database_list").fetchone()[2] or "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "total": 0}
    finally:
        if close_after and conn:
            conn.close()
