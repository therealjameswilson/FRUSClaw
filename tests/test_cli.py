"""CLI smoke tests for the FRUSClaw scaffold."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from frusclaw_cli.main import app


runner = CliRunner()


def test_help_shows_core_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "init",
        "sync",
        "index",
        "search",
        "doc",
        "volume",
        "resolve-url",
        "stats",
    ):
        assert command in result.stdout


def test_init_creates_database_file(tmp_path: Path) -> None:
    db_path = tmp_path / "frusclaw.sqlite3"

    result = runner.invoke(app, ["init", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert db_path.exists()


def test_stats_reports_database_state(tmp_path: Path) -> None:
    db_path = tmp_path / "frusclaw.sqlite3"

    result = runner.invoke(app, ["stats", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert "database exists=False" in result.stdout
