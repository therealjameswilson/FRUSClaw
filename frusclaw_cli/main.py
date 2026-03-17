"""Typer CLI entrypoint for FRUSClaw."""

from __future__ import annotations

from pathlib import Path

import typer

from frusclaw_indexer.database import IndexDatabase

app = typer.Typer(
    help="Local-first research assistant for the FRUS series.",
    no_args_is_help=True,
)


def _placeholder(command_name: str, detail: str) -> None:
    """Emit a consistent scaffold message for incomplete commands."""
    typer.echo(f"{command_name}: {detail}")


@app.command()
def init(db_path: Path = Path("frusclaw.sqlite3")) -> None:
    """Initialize a local FRUSClaw workspace."""
    database = IndexDatabase(db_path)
    database.initialize()
    _placeholder("init", f"initialized local index at {db_path}")


@app.command()
def sync() -> None:
    """Placeholder for future FRUS source synchronization."""
    # TODO: Connect this command to the future OpenClaw-backed sync workflow.
    _placeholder("sync", "source synchronization is not implemented yet")


@app.command()
def index(source: Path | None = None) -> None:
    """Placeholder for future indexing of FRUS source material."""
    target = source or Path(".")
    _placeholder("index", f"indexing pipeline is not implemented yet for {target}")


@app.command()
def search(query: str) -> None:
    """Placeholder for future full-text and metadata search."""
    _placeholder("search", f"search is not implemented yet for query={query!r}")


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
def stats(db_path: Path = Path("frusclaw.sqlite3")) -> None:
    """Show basic local index information."""
    database = IndexDatabase(db_path)
    typer.echo(f"stats: database path={db_path}")
    typer.echo(f"stats: database exists={database.exists()}")


if __name__ == "__main__":
    app()
