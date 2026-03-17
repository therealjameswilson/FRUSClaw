"""Output rendering helpers for FRUSClaw CLI commands."""

from __future__ import annotations

from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.database import IndexDatabase
from frusclaw_indexer.search import SearchResult


def render_search_results(results: list[SearchResult]) -> str:
    """Render search results as concise plain text."""
    if not results:
        return "search: no matches found"

    lines = [f"search: {len(results)} matches"]
    for result in results:
        lines.append(f"- {result.document_id} [{result.volume_id}]")
        if result.headings:
            lines.append(f"  headings: {result.headings}")
        lines.append(f"  snippet: {result.snippet}")
        lines.append(f"  source: {result.source_path}")
    return "\n".join(lines)


def render_stats(config: AppConfig) -> str:
    """Render basic local repository and index state."""
    database = IndexDatabase(config.db_path)
    lines = [
        f"stats: data directory={config.data_dir}",
        f"stats: repository path={config.repo_dir}",
        f"stats: volumes path={config.volumes_dir}",
        f"stats: database path={config.db_path}",
        f"stats: repository exists={(config.repo_dir / '.git').exists()}",
        f"stats: database exists={database.exists()}",
    ]
    if database.exists():
        database.initialize()
        volume_count, document_count = database.get_counts()
        lines.append(f"stats: volume count={volume_count}")
        lines.append(f"stats: document count={document_count}")
    return "\n".join(lines)
