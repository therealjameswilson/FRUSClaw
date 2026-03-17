"""SQLite index building for FRUSClaw."""

from __future__ import annotations

from dataclasses import dataclass

from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.database import DocumentRow, IndexDatabase, VolumeRow
from frusclaw_indexer.parser import ParsedDocument, parse_volume_file


@dataclass(slots=True)
class IndexSummary:
    """Indexing summary for one full rebuild."""

    volume_count: int
    document_count: int


def build_index(config: AppConfig) -> IndexSummary:
    """Rebuild the local SQLite index from FRUS TEI XML volumes."""
    config.ensure_directories()
    if not config.volumes_dir.exists():
        raise RuntimeError(
            f"FRUS volumes directory not found at {config.volumes_dir}. "
            "Run `frusclaw sync` first."
        )

    database = IndexDatabase(config.db_path)
    database.initialize()
    database.reset()

    volume_count = 0
    document_count = 0

    for xml_path in sorted(config.volumes_dir.rglob("*.xml")):
        volume = parse_volume_file(xml_path)
        source_path = str(xml_path.relative_to(config.repo_dir))
        database.insert_volume(
            VolumeRow(
                volume_id=volume.volume_id,
                title=volume.title,
                source_path=source_path,
            )
        )
        document_rows = [
            _to_document_row(document=document, source_path=source_path)
            for document in volume.documents
        ]
        database.insert_documents(document_rows)
        volume_count += 1
        document_count += len(document_rows)

    return IndexSummary(volume_count=volume_count, document_count=document_count)


def _to_document_row(document: ParsedDocument, source_path: str) -> DocumentRow:
    """Convert parsed TEI documents to SQLite rows."""
    return DocumentRow(
        document_id=document.document_id,
        volume_id=document.volume_id,
        volume_title=document.volume_title,
        headings=document.headings,
        plain_text=document.plain_text,
        source_path=source_path,
    )
