"""Simple SQLite search for FRUSClaw."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SearchResult:
    """Search hit returned from the local SQLite index."""

    document_id: str
    volume_id: str
    volume_title: str
    headings: str
    snippet: str
    source_path: str


def search_documents(db_path: Path, query: str, limit: int = 10) -> list[SearchResult]:
    """Search indexed headings and plain text using simple keyword matching."""
    terms = [term.strip().lower() for term in query.split() if term.strip()]
    if not terms:
        return []

    where_clause = " AND ".join(
        "(lower(headings) LIKE ? OR lower(plain_text) LIKE ?)" for _ in terms
    )
    parameters: list[str | int] = []
    for term in terms:
        like_term = f"%{term}%"
        parameters.extend([like_term, like_term])
    parameters.append(limit)

    sql = f"""
        SELECT
            document_id,
            volume_id,
            volume_title,
            headings,
            plain_text,
            source_path
        FROM documents
        WHERE {where_clause}
        ORDER BY volume_id, document_id
        LIMIT ?
    """

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(sql, parameters).fetchall()

    return [
        SearchResult(
            document_id=row[0],
            volume_id=row[1],
            volume_title=row[2],
            headings=row[3],
            snippet=_build_snippet(text=row[4], terms=terms),
            source_path=row[5],
        )
        for row in rows
    ]


def _build_snippet(text: str, terms: list[str], max_length: int = 160) -> str:
    """Build a short plain-text snippet around the first keyword hit."""
    lowered = text.lower()
    first_index = min((lowered.find(term) for term in terms if term in lowered), default=-1)
    if first_index < 0:
        return text[:max_length].strip()

    start = max(first_index - 40, 0)
    end = min(start + max_length, len(text))
    snippet = text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return snippet
