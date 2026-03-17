"""Helpers for FRUS TEI XML ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree


TEI_NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}


@dataclass(slots=True)
class ParsedTEIDocument:
    """Minimal normalized TEI document metadata for future indexing."""

    title: str
    document_id: str | None
    body_text: str


def parse_tei_file(path: Path) -> ParsedTEIDocument:
    """Parse a FRUS TEI XML file into a small internal representation."""
    tree = etree.parse(str(path))
    root = tree.getroot()

    title = _first_text(root, ".//tei:titleStmt/tei:title") or path.stem
    document_id = root.get("{http://www.w3.org/XML/1998/namespace}id")
    body_text = " ".join(root.xpath(".//tei:body//text()", namespaces=TEI_NAMESPACE)).strip()

    return ParsedTEIDocument(
        title=title.strip(),
        document_id=document_id,
        body_text=body_text,
    )


def _first_text(root: etree._Element, xpath: str) -> str | None:
    """Fetch the first text value for a TEI XPath expression."""
    values = root.xpath(xpath + "/text()", namespaces=TEI_NAMESPACE)
    if not values:
        return None
    return str(values[0])


# TODO: Add richer TEI extraction for FRUS volumes, document hierarchy, and notes.
# TODO: Connect parsed output to a future OpenClaw-compatible ingestion workflow.
