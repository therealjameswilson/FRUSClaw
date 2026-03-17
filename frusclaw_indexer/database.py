"""SQLite-ready storage layer for FRUSClaw."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY,
        doc_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        volume_id TEXT,
        source_path TEXT,
        body TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS volumes (
        id INTEGER PRIMARY KEY,
        volume_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        source_path TEXT
    )
    """,
)


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

    def exists(self) -> bool:
        """Return whether the backing SQLite file is present."""
        return self.path.exists()
