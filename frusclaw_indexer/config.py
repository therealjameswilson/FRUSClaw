"""Configuration helpers for local FRUSClaw paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path(".frusclaw")
DEFAULT_REPO_NAME = "frus"
DEFAULT_DB_NAME = "frusclaw.sqlite3"
DEFAULT_REPO_URL = "https://github.com/HistoryAtState/frus.git"


@dataclass(slots=True)
class AppConfig:
    """Resolved local configuration for FRUSClaw commands."""

    data_dir: Path
    repo_dir: Path
    db_path: Path
    repo_url: str = DEFAULT_REPO_URL

    @classmethod
    def from_paths(
        cls,
        data_dir: Path | None = None,
        repo_dir: Path | None = None,
        db_path: Path | None = None,
    ) -> AppConfig:
        """Resolve explicit paths or fall back to local defaults."""
        resolved_data_dir = (data_dir or DEFAULT_DATA_DIR).expanduser().resolve()
        resolved_repo_dir = (repo_dir or resolved_data_dir / DEFAULT_REPO_NAME).expanduser().resolve()
        resolved_db_path = (db_path or resolved_data_dir / DEFAULT_DB_NAME).expanduser().resolve()
        return cls(
            data_dir=resolved_data_dir,
            repo_dir=resolved_repo_dir,
            db_path=resolved_db_path,
        )

    @property
    def volumes_dir(self) -> Path:
        """Return the FRUS TEI volumes directory."""
        return self.repo_dir / "volumes"

    def ensure_directories(self) -> None:
        """Create local directories required for sync and indexing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
