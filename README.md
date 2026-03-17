# FRUSClaw

FRUSClaw is a local-first research assistant for the Foreign Relations of the United States (FRUS) series.

While you work, FRUSClaw is in the archives.

This repository now includes the first working local indexing and search path for FRUS TEI XML volumes, while staying entirely local and without any OpenClaw integration yet. The current goal is to keep the foundation clean and modular for:

- FRUS TEI XML ingestion from the FRUS repository
- Local SQLite indexing
- Keyword search and document lookup workflows
- Future OpenClaw integration

## Current Status

This phase implements a minimal working pipeline:

- `frusclaw sync` prepares a local data directory and clones or updates the FRUS source repository
- `frusclaw index` parses FRUS TEI XML files from `volumes/` and writes normalized records into SQLite
- `frusclaw search "query"` performs simple local keyword search across document headings and plain text

## Project Layout

```text
frusclaw_cli/       Typer-based command-line interface
frusclaw_indexer/   Config, sync, parsing, indexing, search, and rendering
tests/              Parser, index, and search tests
```

## Quick Start

1. Create and activate a Python 3.11+ virtual environment.
2. Install the project in editable mode:

```bash
pip install -e .[dev]
```

3. Prepare local FRUS data:

```bash
frusclaw sync
```

4. Build the SQLite index:

```bash
frusclaw index
```

5. Search locally:

```bash
frusclaw search "berlin"
frusclaw search "arms control"
```

6. Inspect local status:

```bash
frusclaw stats
```

7. Run tests:

```bash
pytest
```

## Local Configuration

By default, FRUSClaw keeps its local state in `.frusclaw/` under the current working directory:

```text
.frusclaw/
  frus/            Local clone of the FRUS repository
  frusclaw.sqlite3 Local SQLite index
```

You can override the defaults per command:

```bash
frusclaw sync --data-dir /tmp/frus-data
frusclaw index --repo-dir /path/to/frus --db-path /tmp/frus.db
frusclaw search "summit" --db-path /tmp/frus.db
```

## Current Scope

- Python 3.11+ only
- Local FRUS repository sync via Git
- TEI XML parsing from `volumes/`
- SQLite indexing for volumes and documents
- Keyword search over headings and plain text
- Parser, indexing, and search tests

## Phase 2 Direction

- Improve TEI extraction fidelity for more FRUS document structures
- Add document and volume detail commands against the SQLite index
- Add incremental indexing and better search ranking
- Connect FRUSClaw to OpenClaw entry points later
