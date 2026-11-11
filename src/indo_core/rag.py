"""RAG Orchestration Layer for LinkedIn Indo.

Bridges the local Vector DB with the LLM drafting engine and Agent tools.
Produces Perplexity-style citations and facts injection blocks.
"""

from __future__ import annotations

from typing import Any
from .vector_db.query import search

MAX_FACTS = 6
MAX_FACT_CHARS = 350
RELEVANCE_THRESHOLD = 0.20


def get_verified_facts(topic: str, n: int = MAX_FACTS) -> list[dict[str, Any]]:
    """Retrieve top-n verified facts for a topic from the personal knowledge base."""
    if not topic or not topic.strip():
        return []
    try:
        results = search(topic, n_results=n)
        return [
            {
                "text": r["excerpt"][:MAX_FACT_CHARS].strip(),
                "source": r["source"],
                "category": r["category"],
                "score": r["score"],
                "file_path": r.get("file_path", "")
            }
            for r in results if r["score"] >= RELEVANCE_THRESHOLD
        ]
    except Exception:
        return []


def facts_block(topic: str) -> str:
    """Format verified facts as an XML block for LLM prompt injection."""
    facts = get_verified_facts(topic)
    if not facts:
        return ""

    lines = ["<verified_personal_facts>"]
    lines.append("  <!-- These are REAL, VERIFIED facts from the user's actual files and PC. Use them accurately: -->")
    for i, f in enumerate(facts, 1):
        pct = int(f["score"] * 100)
        lines.append(f'  <fact index="{i}" source="{f["source"]}" category="{f["category"]}" match="{pct}%">')
        lines.append(f'    {f["text"]}')
        lines.append("  </fact>")
    lines.append("</verified_personal_facts>")
    return "\n".join(lines)


def format_perplexity_results(query: str, results: list[dict[str, Any]]) -> str:
    """Format search results in Perplexity citation style for the Agent and UI."""
    if not results:
        return f'No matching records found in personal knowledge base for: "{query}".'

    lines = [f'### Knowledge Search Results: "{query}"\n']
    for r in results:
        pct = int(r["score"] * 100)
        source = r["source"]
        category = r["category"]
        rank = r.get("rank", 1)
        lines.append(f"**[{rank}] {source}** `[{category}]` — **{pct}% match**")
        if r.get("file_path"):
            lines.append(f"*Path:* `{r['file_path']}`")
        lines.append(f"> {r['excerpt']}\n")

    return "\n".join(lines)
