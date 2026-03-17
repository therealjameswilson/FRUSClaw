"""FRUS research actions exposed to the local agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frusclaw_agent.formatters import format_public_brief, format_research_brief
from frusclaw_agent.providers import ChannelMessage, SkillProvider
from frusclaw_indexer.search import (
    fetch_document,
    fetch_volume,
    fetch_volume_documents,
    resolve_history_state_url,
    search_documents,
)


PUBLIC_MODE = "public"
RESEARCH_MODE = "research"


@dataclass(slots=True)
class FrusResearchService:
    """High-level FRUS research actions over the local SQLite index."""

    db_path: Path

    def search(self, query: str, mode: str = PUBLIC_MODE, limit: int = 5) -> str:
        """Search indexed FRUS documents."""
        results = search_documents(self.db_path, query=query, limit=limit)
        if not results:
            return "No matching FRUS documents were found in the local index."

        lines = [f"Search results for {query!r}:"]
        for result in results:
            if mode == RESEARCH_MODE:
                lines.append(
                    f"- {result.document_id} in {result.volume_id}: {result.headings or 'Untitled'}"
                )
                lines.append(f"  snippet: {result.snippet}")
                lines.append(f"  source: {result.source_path}")
            else:
                label = result.headings or result.volume_title
                lines.append(f"- {label}: {result.snippet}")
        return "\n".join(lines)

    def document(self, document_id: str, mode: str = RESEARCH_MODE) -> str:
        """Retrieve one indexed document."""
        document = fetch_document(self.db_path, document_id)
        if document is None:
            return f"Document {document_id!r} was not found in the local index."

        excerpt = _truncate(document.plain_text, 900 if mode == RESEARCH_MODE else 320)
        if mode == RESEARCH_MODE:
            return "\n".join(
                [
                    f"Document {document.document_id}",
                    f"Volume: {document.volume_id}",
                    f"Volume title: {document.volume_title}",
                    f"Headings: {document.headings or 'None'}",
                    f"Source: {document.source_path}",
                    f"Text: {excerpt}",
                ]
            )
        return f"{document.headings or document.document_id}: {excerpt}"

    def volume(self, volume_id: str, mode: str = RESEARCH_MODE) -> str:
        """Retrieve one indexed volume and a few document references."""
        volume = fetch_volume(self.db_path, volume_id)
        if volume is None:
            return f"Volume {volume_id!r} was not found in the local index."

        documents = fetch_volume_documents(self.db_path, volume_id, limit=8)
        if mode == RESEARCH_MODE:
            lines = [
                f"Volume {volume.volume_id}",
                f"Title: {volume.title}",
                f"Source: {volume.source_path}",
                f"Indexed documents: {len(documents)} shown",
            ]
            for document in documents:
                lines.append(f"- {document.document_id}: {document.headings or 'Untitled'}")
            return "\n".join(lines)

        return f"{volume.title} ({volume.volume_id}) with {len(documents)} indexed documents shown."

    def resolve_url(self, identifier: str, mode: str = RESEARCH_MODE) -> str:
        """Resolve a best-effort history.state.gov URL."""
        url = resolve_history_state_url(self.db_path, identifier)
        if url is None:
            return f"No history.state.gov URL could be resolved for {identifier!r}."
        if mode == RESEARCH_MODE:
            return f"Resolved {identifier!r} to {url}"
        return url

    def reading_pack(self, topic: str, mode: str = RESEARCH_MODE, limit: int = 5) -> str:
        """Build a compact reading pack from matching documents."""
        results = search_documents(self.db_path, query=topic, limit=limit)
        if not results:
            return f"No reading pack could be built for {topic!r}."

        lines = [f"Reading pack for {topic!r}:"]
        for result in results:
            if mode == RESEARCH_MODE:
                lines.append(f"- {result.document_id} [{result.volume_id}] {result.headings or 'Untitled'}")
                lines.append(f"  snippet: {result.snippet}")
            else:
                lines.append(f"- {result.headings or result.volume_title}")
        return "\n".join(lines)

    def timeline(self, topic: str, mode: str = RESEARCH_MODE, limit: int = 8) -> str:
        """Build a simple document-order timeline for one topic."""
        results = search_documents(self.db_path, query=topic, limit=limit)
        if not results:
            return f"No timeline entries were found for {topic!r}."

        lines = [f"Timeline for {topic!r} (ordered by indexed document ID):"]
        for position, result in enumerate(results, start=1):
            if mode == RESEARCH_MODE:
                lines.append(
                    f"{position}. {result.document_id} [{result.volume_id}] {result.headings or 'Untitled'}"
                )
            else:
                lines.append(f"{position}. {result.headings or result.volume_title}")
        return "\n".join(lines)

    def daily_brief(self, topic: str, mode: str = RESEARCH_MODE) -> str:
        """Generate a simple explainable brief from top FRUS search hits."""
        results = search_documents(self.db_path, query=topic, limit=3)
        if mode == RESEARCH_MODE:
            return format_research_brief(topic, results)
        return format_public_brief(topic, results)


class FrusSkillProvider(SkillProvider):
    """Default FRUS skill provider for agent messages."""

    def __init__(self, service: FrusResearchService) -> None:
        self.service = service

    @property
    def name(self) -> str:
        return "frus-research"

    def can_handle(self, message: ChannelMessage) -> bool:
        return bool(message.text.strip())

    def handle(self, message: ChannelMessage) -> str:
        command, argument = _split_command(message.text)
        if command == "search":
            return self.service.search(argument, mode=message.mode)
        if command == "doc":
            return self.service.document(argument, mode=message.mode)
        if command == "volume":
            return self.service.volume(argument, mode=message.mode)
        if command == "resolve":
            return self.service.resolve_url(argument, mode=message.mode)
        if command == "reading-pack":
            return self.service.reading_pack(argument, mode=message.mode)
        if command == "timeline":
            return self.service.timeline(argument, mode=message.mode)
        if command == "daily-brief":
            return self.service.daily_brief(argument, mode=message.mode)
        return self.service.search(message.text, mode=message.mode)


def _split_command(text: str) -> tuple[str, str]:
    """Split a message into a command keyword and the remaining argument."""
    stripped = text.strip()
    if not stripped:
        return "search", ""
    normalized = stripped[1:] if stripped.startswith("/") else stripped
    command, _, argument = normalized.partition(" ")
    return command.lower(), argument.strip()


def _truncate(text: str, limit: int) -> str:
    """Trim long text blocks for terminal or channel responses."""
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."
