"""Local Git operations for FRUSClaw repository sync."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from frusclaw_indexer.config import AppConfig


@dataclass(slots=True)
class SyncResult:
    """Summary of a repository sync action."""

    action: str
    message: str
    repo_path: Path


def ensure_frus_repository(config: AppConfig) -> SyncResult:
    """Clone the FRUS repository if missing, otherwise update it locally."""
    config.ensure_directories()

    if (config.repo_dir / ".git").exists():
        try:
            _run_git(["pull", "--ff-only"], cwd=config.repo_dir)
        except RuntimeError as error:
            raise RuntimeError(
                f"failed to update FRUS repository at {config.repo_dir}: {error}"
            ) from error
        return SyncResult(
            action="updated",
            message="updated existing FRUS repository",
            repo_path=config.repo_dir,
        )

    if config.repo_dir.exists() and any(config.repo_dir.iterdir()):
        raise RuntimeError(f"repository path exists and is not an empty Git clone: {config.repo_dir}")

    try:
        _run_git(["clone", "--depth", "1", config.repo_url, str(config.repo_dir)])
    except RuntimeError as error:
        raise RuntimeError(
            f"failed to clone FRUS repository from {config.repo_url} into {config.repo_dir}: {error}"
        ) from error
    return SyncResult(
        action="cloned",
        message="cloned FRUS repository",
        repo_path=config.repo_dir,
    )


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a Git command and surface stderr on failure."""
    command = ["git", *args]
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(message)
    return result.stdout.strip()
