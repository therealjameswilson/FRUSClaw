# FRUSClaw project instructions

FRUSClaw is a local-first research agent for the Foreign Relations of the United States (FRUS) series.

Project goals:
- Build a Python-based FRUS indexing and retrieval system
- Prepare for integration with OpenClaw later
- Keep the repo safe, readable, and modular
- Favor incremental changes over giant rewrites
- Always explain planned file changes before making them

Technical preferences:
- Python 3.11+
- Typer for CLI
- lxml for TEI XML parsing
- SQLite for MVP indexing/search
- pytest for tests
- Clear README and setup docs

Behavior rules:
- Do not delete files unless explicitly asked
- Do not add unnecessary dependencies
- Keep functions small and well commented
- Ask for approval before destructive shell commands
- When uncertain, scaffold first and leave TODOs
