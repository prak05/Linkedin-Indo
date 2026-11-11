"""Unit tests for the Vector DB, Hybrid Search, and RAG layer."""

import sqlite3
import pytest
from indo_core.vector_db.db import (
    compute_vector,
    cosine_similarity,
    get_connection,
    init_db,
    tokenize,
)
from indo_core.vector_db.ingest import chunk_text
from indo_core.vector_db.query import search, stats
from indo_core.rag import format_perplexity_results, get_verified_facts, facts_block


def test_tokenize_and_vector():
    tokens = tokenize("KSERC AI Truing-Up Tool Regulatory Automation")
    assert "kserc" in tokens
    assert "regulatory" in tokens
    assert "kserc_ai" in tokens
    vec, norm = compute_vector(tokens)
    assert "kserc" in vec
    assert norm > 0.0


def test_cosine_similarity():
    v1, n1 = compute_vector(tokenize("AWS CloudConnect Trivandrum CareStack"))
    v2, n2 = compute_vector(tokenize("CareStack hosted AWS CloudConnect event"))
    v3, n3 = compute_vector(tokenize("Completely unrelated baking recipe cake flour"))

    sim_related = cosine_similarity(v1, n1, v2, n2)
    sim_unrelated = cosine_similarity(v1, n1, v3, n3)

    assert sim_related > 0.3
    assert sim_unrelated == 0.0


def test_chunking():
    sample = "word " * 600
    chunks = chunk_text(sample, chunk_size=200, overlap=30)
    assert len(chunks) >= 3


def test_in_memory_hybrid_search(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    conn = get_connection(db_file)
    init_db(conn)

    # Insert two test chunks
    with conn:
        for idx, (src, cat, heading, text) in enumerate([
            ("KSERC Order", "kserc", "Tariff Order", "Kerala State Electricity Regulatory Commission tariff truing up automation tool."),
            ("AWS SBGL", "aws_event", "CloudConnect", "AWS Student Builder Group Leader convened Builder CloudConnect Trivandrum at CareStack."),
        ]):
            toks = tokenize(f"{heading} {text}")
            vec, norm = compute_vector(toks)
            import json
            conn.execute("""
                INSERT INTO chunks (id, source, file_path, category, heading, content, tokens_json, norm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"id_{idx}", src, "/path", cat, heading, text, json.dumps(vec), norm))

    # Query 1
    res1 = search("KSERC electricity regulatory", n_results=3, conn=conn)
    assert len(res1) >= 1
    assert res1[0]["source"] == "KSERC Order"

    # Query 2 with category filter
    res2 = search("CloudConnect CareStack", n_results=3, category_filter="aws_event", conn=conn)
    assert len(res2) >= 1
    assert res2[0]["source"] == "AWS SBGL"

    # Perplexity formatting
    formatted = format_perplexity_results("CloudConnect CareStack", res2)
    assert "[1] AWS SBGL" in formatted
    assert "match" in formatted

    conn.close()


def test_agent_search_my_knowledge_tool():
    from indo_core import agent
    # Tool exists in agent.TOOLS
    tool_names = [t["name"] for t in agent.TOOLS]
    assert "search_my_knowledge" in tool_names

    # Calling tool returns results or clean message
    out = agent.search_my_knowledge("KSERC")
    assert isinstance(out, str)
    assert len(out) > 0
