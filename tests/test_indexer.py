"""Parser, indexing, and search tests for FRUSClaw."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from frusclaw_cli.main import app
from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.indexer import build_index
from frusclaw_indexer.parser import parse_volume_file
from frusclaw_indexer.search import search_documents


SAMPLE_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="frus-test-volume">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Foreign Relations of the United States, Test Volume</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="document" xml:id="doc-1">
        <head>Memorandum of Conversation</head>
        <p>The Berlin crisis remained central to the discussion.</p>
      </div>
      <div type="document" xml:id="doc-2">
        <head>Telegram From Bonn</head>
        <p>Officials discussed trade policy and alliance strategy.</p>
      </div>
    </body>
  </text>
</TEI>
"""


runner = CliRunner()


def test_parse_volume_file_extracts_basic_fields(tmp_path: Path) -> None:
    xml_path = _write_sample_volume(tmp_path)

    volume = parse_volume_file(xml_path)

    assert volume.volume_id == "frus-test-volume"
    assert volume.title == "Foreign Relations of the United States, Test Volume"
    assert len(volume.documents) == 2
    assert volume.documents[0].document_id == "doc-1"
    assert volume.documents[0].headings == "Memorandum of Conversation"
    assert "Berlin crisis remained central" in volume.documents[0].plain_text


def test_build_index_creates_volume_and_document_rows(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _write_sample_volume(config.volumes_dir)

    summary = build_index(config)

    assert summary.volume_count == 1
    assert summary.document_count == 2

    with sqlite3.connect(config.db_path) as connection:
        volume_count = connection.execute("SELECT COUNT(*) FROM volumes").fetchone()[0]
        document_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        source_path = connection.execute(
            "SELECT source_path FROM documents WHERE document_id = 'doc-1'"
        ).fetchone()[0]

    assert volume_count == 1
    assert document_count == 2
    assert source_path == "volumes/test-volume.xml"


def test_search_documents_finds_keyword_hits(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _write_sample_volume(config.volumes_dir)
    build_index(config)

    results = search_documents(config.db_path, "Berlin")

    assert len(results) == 1
    assert results[0].document_id == "doc-1"
    assert "Berlin crisis" in results[0].snippet


def test_index_command_reports_missing_volumes_directory(tmp_path: Path) -> None:
    data_dir = tmp_path / ".frusclaw"
    repo_dir = data_dir / "frus"
    repo_dir.mkdir(parents=True)
    db_path = data_dir / "frusclaw.sqlite3"

    result = runner.invoke(
        app,
        [
            "index",
            "--data-dir",
            str(data_dir),
            "--repo-dir",
            str(repo_dir),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Run `frusclaw sync` first." in result.stderr


def _build_config(tmp_path: Path) -> AppConfig:
    data_dir = tmp_path / ".frusclaw"
    repo_dir = data_dir / "frus"
    volumes_dir = repo_dir / "volumes"
    volumes_dir.mkdir(parents=True)
    return AppConfig.from_paths(
        data_dir=data_dir,
        repo_dir=repo_dir,
        db_path=data_dir / "frusclaw.sqlite3",
    )


def _write_sample_volume(base_dir: Path) -> Path:
    if base_dir.name == "volumes":
        volumes_dir = base_dir
    else:
        volumes_dir = base_dir / "volumes"
        volumes_dir.mkdir(parents=True, exist_ok=True)
    xml_path = volumes_dir / "test-volume.xml"
    xml_path.write_text(SAMPLE_TEI, encoding="utf-8")
    return xml_path
