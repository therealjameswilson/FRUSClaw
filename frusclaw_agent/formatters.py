"""Reusable formatters for FRUSClaw brief output."""

from __future__ import annotations

from frusclaw_indexer.search import SearchResult


def format_public_brief(topic: str, results: list[SearchResult]) -> str:
    """Render a concise public-facing brief."""
    if not results:
        return f"No FRUS documents were found for {topic!r}."

    lines = [f"Brief for {topic!r}:"]
    for result in results:
        title = result.headings or result.volume_title
        lines.append(f"- {title}: {result.snippet}")
    return "\n".join(lines)


def format_research_brief(topic: str, results: list[SearchResult]) -> str:
    """Render a citation-rich research brief."""
    if not results:
        return f"No FRUS documents were found for {topic!r}."

    lines = [f"Research brief for {topic!r}:"]
    for result in results:
        lines.append(f"- {result.document_id} [{result.volume_id}] {result.headings or 'Untitled'}")
        lines.append(f"  snippet: {result.snippet}")
        lines.append(f"  source: {result.source_path}")
    return "\n".join(lines)
