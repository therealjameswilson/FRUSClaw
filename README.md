# FRUSClaw

FRUSClaw is a local-first research assistant for the Foreign Relations of the United States (FRUS) series.

While you work, FRUSClaw is in the archives.

This repository is the first scaffold for a Python-based indexing and retrieval system. The current goal is to establish a clean, modular foundation for:

- FRUS TEI XML ingestion
- Local SQLite indexing
- Search and document lookup workflows
- Future OpenClaw integration

## Current Status

This phase intentionally scaffolds the project without implementing a full ingestion or search pipeline yet. The CLI commands are placeholders wired for future expansion, and the indexer package includes minimal TEI parsing and SQLite-ready storage helpers.

## Project Layout

```text
frusclaw_cli/       Typer-based command-line interface
frusclaw_indexer/   Parsing and indexing foundations
tests/              Pytest smoke tests
```

## Quick Start

1. Create and activate a Python 3.11+ virtual environment.
2. Install the project in editable mode:

```bash
pip install -e .[dev]
```

3. Explore the CLI:

```bash
frusclaw --help
frusclaw init
frusclaw stats
```

4. Run tests:

```bash
pytest
```

## Phase 1 Scope

- Minimal Typer CLI with placeholder commands
- Parser module prepared for FRUS TEI XML ingestion using `lxml`
- SQLite-ready indexing layer
- Basic CLI smoke tests

## Phase 2 Direction

- Implement FRUS volume discovery and synchronization
- Ingest TEI XML into normalized SQLite tables
- Add real search, document retrieval, and volume inspection
- Connect FRUSClaw to OpenClaw entry points
