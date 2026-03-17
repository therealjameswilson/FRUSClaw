"""Typer CLI entrypoint for FRUSClaw."""

from __future__ import annotations

from pathlib import Path

import typer

from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.database import IndexDatabase
from frusclaw_indexer.git_ops import ensure_frus_repository
from frusclaw_indexer.indexer import build_index
from frusclaw_indexer.render import render_search_results, render_stats
from frusclaw_indexer.search import search_documents

app = typer.Typer(
    help="Local-first research assistant for the FRUS series.",
    no_args_is_help=True,
)


def _placeholder(command_name: str, detail: str) -> None:
    """Emit a consistent scaffold message for incomplete commands."""
    typer.echo(f"{command_name}: {detail}")


def _config_options(
    data_dir: Path | None = None,
    repo_dir: Path | None = None,
    db_path: Path | None = None,
) -> AppConfig:
    """Resolve command configuration from explicit paths or defaults."""
    return AppConfig.from_paths(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)


@app.command()
def init(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Initialize a local FRUSClaw workspace."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    config.ensure_directories()
    IndexDatabase(config.db_path).initialize()
    typer.echo(f"init: data directory={config.data_dir}")
    typer.echo(f"init: repository path={config.repo_dir}")
    typer.echo(f"init: database path={config.db_path}")


@app.command()
def sync(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Prepare local FRUS data and sync the FRUS repository."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    result = ensure_frus_repository(config)
    typer.echo(f"sync: data directory={config.data_dir}")
    typer.echo(f"sync: repository path={result.repo_path}")
    typer.echo(f"sync: action={result.action}")


@app.command()
def index(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Parse FRUS TEI volumes and populate the local SQLite index."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    summary = build_index(config)
    typer.echo(f"index: volumes indexed={summary.volume_count}")
    typer.echo(f"index: documents indexed={summary.document_count}")
    typer.echo(f"index: database path={config.db_path}")


@app.command()
def search(
    query: str,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    limit: int = typer.Option(10, min=1, max=100, help="Maximum number of search results."),
) -> None:
    """Search headings and full text in the local SQLite index."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    results = search_documents(config.db_path, query=query, limit=limit)
    typer.echo(render_search_results(results))


@app.command("doc")
def doc_command(doc_id: str) -> None:
    """Placeholder for future document retrieval."""
    _placeholder("doc", f"document lookup is not implemented yet for doc_id={doc_id!r}")


@app.command()
def volume(volume_id: str) -> None:
    """Placeholder for future volume retrieval."""
    _placeholder("volume", f"volume lookup is not implemented yet for volume_id={volume_id!r}")


@app.command("resolve-url")
def resolve_url(identifier: str) -> None:
    """Placeholder for future FRUS identifier to URL resolution."""
    _placeholder(
        "resolve-url",
        f"URL resolution is not implemented yet for identifier={identifier!r}",
    )


@app.command()
def stats(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Show basic local index information."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    typer.echo(render_stats(config))


if __name__ == "__main__":
    app()
