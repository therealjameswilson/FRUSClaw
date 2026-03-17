# FRUSClaw

FRUSClaw is a local-first research assistant for the Foreign Relations of the United States (FRUS) series.

While you work, FRUSClaw is in the archives.

FRUSClaw is an OpenClaw-style architecture for FRUS research, not a clone of OpenClaw itself. The existing Python FRUS core stays intact, and a small local agent layer sits above it.

## Architecture Overview

- FRUSClaw core: Python CLI plus local FRUS sync, TEI parsing, SQLite indexing, and search.
- FRUSClaw agent: a minimal always-on local skeleton that loads config, tracks state, and runs a safe foreground loop.
- FRUSClaw runtime: local-first and single-user by default on the user’s own machine.
- Future direction: add channels and richer agent behaviors later without replacing the FRUS core.

## Current Phase

Phase 3E adds:

- `frusclaw setup`
- env-driven config support
- `frusclaw agent start|stop|status`
- a background local agent loop with pid/state tracking
- recurring local brief jobs in SQLite
- `frusclaw jobs list` and `frusclaw jobs remove`
- a Telegram-first channel scaffold with allowlist enforcement
- `frusclaw telegram check-config` and `frusclaw telegram run`
- a WhatsApp Cloud API scaffold with webhook verification and outbound text sending
- `frusclaw whatsapp check-config`, `status`, `webhook`, and `send-test`

Existing FRUS core functionality remains:

- `frusclaw sync`
- `frusclaw index`
- `frusclaw search`
- `frusclaw doc`
- `frusclaw volume`
- `frusclaw resolve-url`
- `frusclaw brief`

## Project Layout

```text
frusclaw_cli/       Typer CLI commands
frusclaw_indexer/   FRUS sync, parsing, indexing, search, and rendering
frusclaw_agent/     Agent skeleton, config, models, router, and scheduler
tests/              Indexer and agent tests
```

## First Run

1. Create and activate a Python 3.11+ virtual environment.
2. Install the project:

```bash
pip install -e .[dev]
```

3. Create local FRUSClaw scaffolding:

```bash
frusclaw setup
```

4. Sync FRUS data:

```bash
frusclaw sync
```

5. Build the local index:

```bash
frusclaw index
```

6. Run the always-on local agent:

```bash
frusclaw agent start
frusclaw agent status
frusclaw agent stop
```

7. Create and manage recurring briefs:

```bash
frusclaw brief --topic "Berlin crisis" --daily
frusclaw brief --topic "arms control" --weekly --mode public
frusclaw jobs list
frusclaw jobs remove 1
```

## Local Files

By default, FRUSClaw stores local state in `.frusclaw/`:

```text
.frusclaw/
  config.toml
  .env.example
  frus/
  frusclaw.sqlite3
  agent.pid
  agent-state.json
  agent.log
```

## Environment Variables

FRUSClaw supports:

- `FRUSCLAW_DATA_DIR`
- `FRUSCLAW_DB_PATH`
- `FRUSCLAW_REPO_DIR`
- `FRUSCLAW_MODE`
- `TELEGRAM_BOT_TOKEN`
- `FRUSCLAW_ALLOWED_USERS`
- `TELEGRAM_POLL_INTERVAL`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_API_VERSION`
- `WHATSAPP_WEBHOOK_HOST`
- `WHATSAPP_WEBHOOK_PORT`

Example:

```bash
export FRUSCLAW_DATA_DIR="$HOME/.frusclaw"
export FRUSCLAW_REPO_DIR="$HOME/.frusclaw/frus"
export FRUSCLAW_DB_PATH="$HOME/.frusclaw/frusclaw.sqlite3"
export FRUSCLAW_MODE="research"
export TELEGRAM_BOT_TOKEN=""
export FRUSCLAW_ALLOWED_USERS="alice,bob"
export TELEGRAM_POLL_INTERVAL="30"
export WHATSAPP_ACCESS_TOKEN=""
export WHATSAPP_PHONE_NUMBER_ID=""
export WHATSAPP_VERIFY_TOKEN=""
export WHATSAPP_APP_SECRET=""
export WHATSAPP_API_VERSION="v20.0"
export WHATSAPP_WEBHOOK_HOST="127.0.0.1"
export WHATSAPP_WEBHOOK_PORT="8000"
```

## Config Files

- [frusclaw.sample.toml](/Users/jameswilson/Projects/frusclaw/frusclaw.sample.toml) shows the default local agent config shape.
- [.env.example](/Users/jameswilson/Projects/frusclaw/.env.example) shows supported environment variables.

## Safety

- Python 3.11+ only
- Local-first and single-user by default
- Read-only FRUS operations
- No OpenClaw dependency
- No arbitrary destructive shell behavior
- One local background agent instance per data directory

## Current Limitations

- The agent is a skeleton, not a full assistant runtime yet.
- Telegram is still a scaffold, not a production bot yet.
- WhatsApp is a first working scaffold, not a production bot yet.
- No local web chat server is required in Phase 3E.
- No embeddings yet.

## Always-On Mode

The background agent is intended for local development and personal-machine use. It keeps a pid file and state file in `.frusclaw/`, loads scheduled jobs from SQLite, runs pending briefs, and writes activity to `agent.log`.

Commands:

```bash
frusclaw agent start
frusclaw agent status
frusclaw agent stop
```

The agent status command reports:

- whether the agent is running
- the current pid
- whether scheduled jobs are active
- how many scheduled jobs are loaded
- whether Telegram mode is configured
- where logs are being written

## Logs And Troubleshooting

Local runtime files:

- `.frusclaw/agent.pid`
- `.frusclaw/agent-state.json`
- `.frusclaw/agent.log`

If the agent appears stuck:

```bash
frusclaw agent status
tail -n 50 .frusclaw/agent.log
```

If FRUS briefs are not running:

- check that jobs exist with `frusclaw jobs list`
- confirm the agent is running with `frusclaw agent status`
- confirm the FRUS index exists and is current

## Telegram Scaffold

FRUSClaw now includes a Telegram-first channel scaffold with clean interfaces for later channels.

Setup placeholders:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export FRUSCLAW_ALLOWED_USERS="your-telegram-username"
export TELEGRAM_POLL_INTERVAL="30"
```

Check the scaffold configuration:

```bash
frusclaw telegram check-config
```

Run the scaffold:

```bash
frusclaw telegram run
```

Security notes:

- FRUSClaw is intended for personal-machine use.
- Only allowlisted users should be able to interact with the Telegram scaffold.
- Unauthorized users receive a simple denial response.
- All FRUS actions remain read-only.

## WhatsApp Scaffold

FRUSClaw now includes a WhatsApp Cloud API style scaffold built around:

- inbound webhook verification
- inbound webhook payload parsing
- sender allowlist enforcement
- outbound text replies through the Graph API
- reuse of the same FRUS action layer used by other channels

WhatsApp Cloud API setup placeholders:

```bash
export WHATSAPP_ACCESS_TOKEN="your-access-token"
export WHATSAPP_PHONE_NUMBER_ID="your-phone-number-id"
export WHATSAPP_VERIFY_TOKEN="your-local-verify-token"
export WHATSAPP_APP_SECRET=""
export WHATSAPP_API_VERSION="v20.0"
export WHATSAPP_WEBHOOK_HOST="127.0.0.1"
export WHATSAPP_WEBHOOK_PORT="8000"
```

Check configuration and status:

```bash
frusclaw whatsapp check-config
frusclaw whatsapp status
```

Run the local webhook listener:

```bash
frusclaw whatsapp webhook
```

Send a test message through the configured Cloud API credentials:

```bash
frusclaw whatsapp send-test --to 15551234567
```

Webhook verification notes:

- configure the Meta webhook verify token to match `WHATSAPP_VERIFY_TOKEN`
- point the Meta webhook callback to your local listener through your preferred tunnel or local routing
- if `WHATSAPP_APP_SECRET` is set, FRUSClaw verifies the `X-Hub-Signature-256` header

Security notes:

- FRUSClaw is intended for personal-machine use
- keep `FRUSCLAW_ALLOWED_USERS` restricted to your own approved phone numbers
- unauthorized senders receive a simple denial response
- all FRUS actions remain read-only

Troubleshooting:

- if `whatsapp check-config` fails, fill in the missing credentials it reports
- if outbound sends fail, confirm the access token, phone number ID, and API version
- if webhook verification fails, confirm the verify token and optional app secret

## Roadmap To Fuller OpenClaw-Style Parity

- real Telegram polling/webhooks instead of scaffold-only validation
- real WhatsApp webhook deployment and delivery retries
- richer background orchestration and message delivery
- more robust daemon/service integration for startup-on-login
- local chat or web chat surface on top of the same action layer
- stronger observability, retries, and failure handling
- broader channel support beyond Telegram and WhatsApp

## Recurring Briefs

FRUSClaw stores scheduled jobs in the local SQLite database. The scheduler currently supports:

- `once`
- `daily`
- `weekly`

Examples:

```bash
frusclaw brief --topic "Berlin" --daily
frusclaw brief --topic "NATO" --weekly --mode research
frusclaw jobs list
frusclaw jobs remove 2
```

One-off briefs still run without creating a scheduled job:

```bash
frusclaw brief --topic "Berlin" --mode public
frusclaw brief --topic "Berlin" --mode research
```
