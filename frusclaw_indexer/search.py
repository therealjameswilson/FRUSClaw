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


@dataclass(slots=True)
class DocumentRecord:
    """Indexed FRUS document record."""

    document_id: str
    volume_id: str
    volume_title: str
    headings: str
    plain_text: str
    source_path: str


@dataclass(slots=True)
class VolumeRecord:
    """Indexed FRUS volume record."""

    volume_id: str
    title: str
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


def fetch_document(db_path: Path, document_id: str) -> DocumentRecord | None:
    """Return one indexed document by ID."""
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT document_id, volume_id, volume_title, headings, plain_text, source_path
            FROM documents
            WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()
    if row is None:
        return None
    return DocumentRecord(*row)


def fetch_volume(db_path: Path, volume_id: str) -> VolumeRecord | None:
    """Return one indexed volume by ID."""
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT volume_id, title, source_path FROM volumes WHERE volume_id = ?",
            (volume_id,),
        ).fetchone()
    if row is None:
        return None
    return VolumeRecord(*row)


def fetch_volume_documents(db_path: Path, volume_id: str, limit: int = 25) -> list[DocumentRecord]:
    """Return indexed documents for one volume."""
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT document_id, volume_id, volume_title, headings, plain_text, source_path
            FROM documents
            WHERE volume_id = ?
            ORDER BY document_id
            LIMIT ?
            """,
            (volume_id, limit),
        ).fetchall()
    return [DocumentRecord(*row) for row in rows]


def resolve_history_state_url(db_path: Path, identifier: str) -> str | None:
    """Best-effort FRUS URL resolution for a volume or document identifier."""
    document = fetch_document(db_path, identifier)
    if document is not None:
        return f"https://history.state.gov/historicaldocuments/{document.volume_id}#{document.document_id}"

    volume = fetch_volume(db_path, identifier)
    if volume is not None:
        return f"https://history.state.gov/historicaldocuments/{volume.volume_id}"

    return None


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
