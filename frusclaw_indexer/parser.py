"""Helpers for FRUS TEI XML ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree


TEI_NAMESPACE = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


@dataclass(slots=True)
class ParsedDocument:
    """Normalized FRUS document content extracted from a TEI volume."""

    volume_id: str
    volume_title: str
    document_id: str
    headings: str
    plain_text: str


@dataclass(slots=True)
class ParsedVolume:
    """Normalized FRUS volume content ready for indexing."""

    volume_id: str
    title: str
    documents: list[ParsedDocument]


def parse_volume_file(path: Path) -> ParsedVolume:
    """Parse a FRUS TEI XML volume into indexable records."""
    tree = etree.parse(str(path))
    root = tree.getroot()

    volume_id = root.get("{http://www.w3.org/XML/1998/namespace}id") or path.stem
    volume_title = _first_text(root, ".//tei:titleStmt/tei:title") or path.stem

    document_nodes = root.xpath(".//tei:text/tei:body/tei:div[@type='document']", namespaces=TEI_NAMESPACE)
    if not document_nodes:
        document_nodes = root.xpath(".//tei:text/tei:body/tei:div", namespaces=TEI_NAMESPACE)

    documents: list[ParsedDocument] = []
    for index, node in enumerate(document_nodes, start=1):
        document_id = node.get("{http://www.w3.org/XML/1998/namespace}id") or f"{volume_id}-doc-{index}"
        headings = _normalize_whitespace(" ".join(node.xpath(".//tei:head//text()", namespaces=TEI_NAMESPACE)))
        plain_text = _extract_plain_text(node)
        documents.append(
            ParsedDocument(
                volume_id=volume_id,
                volume_title=_normalize_whitespace(volume_title),
                document_id=document_id,
                headings=headings,
                plain_text=plain_text,
            )
        )

    if not documents:
        body = root.xpath(".//tei:text/tei:body", namespaces=TEI_NAMESPACE)
        body_text = _extract_plain_text(body[0]) if body else ""
        documents.append(
            ParsedDocument(
                volume_id=volume_id,
                volume_title=_normalize_whitespace(volume_title),
                document_id=f"{volume_id}-doc-1",
                headings="",
                plain_text=body_text,
            )
        )

    return ParsedVolume(
        volume_id=volume_id,
        title=_normalize_whitespace(volume_title),
        documents=documents,
    )


def _extract_plain_text(node: etree._Element) -> str:
    """Extract plain text while excluding heading text from the body copy."""
    text_parts = node.xpath(".//text()[not(ancestor::tei:head)]", namespaces=TEI_NAMESPACE)
    return _normalize_whitespace(" ".join(text_parts))


def _first_text(root: etree._Element, xpath: str) -> str | None:
    """Fetch the first text value for a TEI XPath expression."""
    values = root.xpath(f"{xpath}/text()", namespaces=TEI_NAMESPACE)
    if not values:
        return None
    return str(values[0])


def _normalize_whitespace(value: str) -> str:
    """Collapse internal whitespace for cleaner indexing."""
    return " ".join(value.split())


# TODO: Add richer TEI extraction for notes, people, places, and structured metadata.
# TODO: Detect more FRUS document container variants if needed across historical volumes.
