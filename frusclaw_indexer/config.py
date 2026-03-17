"""Configuration helpers for local FRUSClaw paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path(".frusclaw")
DEFAULT_REPO_NAME = "frus"
DEFAULT_DB_NAME = "frusclaw.sqlite3"
DEFAULT_REPO_URL = "https://github.com/HistoryAtState/frus.git"
DEFAULT_CONFIG_NAME = "config.toml"
DEFAULT_ENV_NAME = ".env"
DEFAULT_ENV_EXAMPLE_NAME = ".env.example"
DEFAULT_AGENT_STATE_NAME = "agent-state.json"
DEFAULT_AGENT_PID_NAME = "agent.pid"
DEFAULT_AGENT_LOG_NAME = "agent.log"


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
        """Resolve explicit paths or fall back to local defaults and env vars."""
        raw_data_dir = data_dir or os.environ.get("FRUSCLAW_DATA_DIR") or DEFAULT_DATA_DIR
        resolved_data_dir = Path(raw_data_dir).expanduser().resolve()
        raw_repo_dir = repo_dir or os.environ.get("FRUSCLAW_REPO_DIR") or resolved_data_dir / DEFAULT_REPO_NAME
        resolved_repo_dir = Path(raw_repo_dir).expanduser().resolve()
        raw_db_path = db_path or os.environ.get("FRUSCLAW_DB_PATH") or resolved_data_dir / DEFAULT_DB_NAME
        resolved_db_path = Path(raw_db_path).expanduser().resolve()
        return cls(
            data_dir=resolved_data_dir,
            repo_dir=resolved_repo_dir,
            db_path=resolved_db_path,
        )

    @property
    def volumes_dir(self) -> Path:
        """Return the FRUS TEI volumes directory."""
        return self.repo_dir / "volumes"

    @property
    def config_path(self) -> Path:
        """Return the local FRUSClaw agent config path."""
        return self.data_dir / DEFAULT_CONFIG_NAME

    @property
    def env_path(self) -> Path:
        """Return the local FRUSClaw environment file path."""
        return self.data_dir / DEFAULT_ENV_NAME

    @property
    def env_example_path(self) -> Path:
        """Return the local FRUSClaw example environment file path."""
        return self.data_dir / DEFAULT_ENV_EXAMPLE_NAME

    @property
    def agent_state_path(self) -> Path:
        """Return the local FRUSClaw agent state file path."""
        return self.data_dir / DEFAULT_AGENT_STATE_NAME

    @property
    def agent_pid_path(self) -> Path:
        """Return the local FRUSClaw agent pid file path."""
        return self.data_dir / DEFAULT_AGENT_PID_NAME

    @property
    def agent_log_path(self) -> Path:
        """Return the local FRUSClaw agent log file path."""
        return self.data_dir / DEFAULT_AGENT_LOG_NAME

    def ensure_directories(self) -> None:
        """Create local directories required for sync and indexing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
