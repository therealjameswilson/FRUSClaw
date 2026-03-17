"""SQLite-ready storage layer for FRUSClaw."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS volumes (
        volume_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        source_path TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        volume_id TEXT NOT NULL,
        volume_title TEXT NOT NULL,
        headings TEXT NOT NULL,
        plain_text TEXT NOT NULL,
        source_path TEXT NOT NULL,
        FOREIGN KEY (volume_id) REFERENCES volumes (volume_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_documents_volume_id ON documents (volume_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_source_path ON documents (source_path)",
)


@dataclass(slots=True)
class VolumeRow:
    """SQLite row payload for a FRUS volume."""

    volume_id: str
    title: str
    source_path: str


@dataclass(slots=True)
class DocumentRow:
    """SQLite row payload for a FRUS document."""

    document_id: str
    volume_id: str
    volume_title: str
    headings: str
    plain_text: str
    source_path: str


class IndexDatabase:
    """Thin wrapper around the local SQLite index."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        """Open a connection to the configured SQLite database."""
        return sqlite3.connect(self.path)

    def initialize(self) -> None:
        """Create the minimal schema required for the first scaffold."""
        with self.connect() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.commit()

    def reset(self) -> None:
        """Clear indexed content before a full rebuild."""
        with self.connect() as connection:
            connection.execute("DELETE FROM documents")
            connection.execute("DELETE FROM volumes")
            connection.commit()

    def insert_volume(self, row: VolumeRow) -> None:
        """Insert or replace a volume row."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO volumes (volume_id, title, source_path)
                VALUES (?, ?, ?)
                """,
                (row.volume_id, row.title, row.source_path),
            )
            connection.commit()

    def insert_documents(self, rows: list[DocumentRow]) -> None:
        """Insert or replace document rows."""
        if not rows:
            return
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO documents (
                    document_id,
                    volume_id,
                    volume_title,
                    headings,
                    plain_text,
                    source_path
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.document_id,
                        row.volume_id,
                        row.volume_title,
                        row.headings,
                        row.plain_text,
                        row.source_path,
                    )
                    for row in rows
                ],
            )
            connection.commit()

    def get_counts(self) -> tuple[int, int]:
        """Return indexed volume and document counts."""
        with self.connect() as connection:
            volume_count = connection.execute("SELECT COUNT(*) FROM volumes").fetchone()[0]
            document_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return volume_count, document_count

    def exists(self) -> bool:
        """Return whether the backing SQLite file is present."""
        return self.path.exists()
