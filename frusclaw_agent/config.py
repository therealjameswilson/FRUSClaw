"""Agent configuration loading and local setup helpers."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from frusclaw_agent.models import AgentSettings
from frusclaw_indexer.config import AppConfig


DEFAULT_CONFIG_TEMPLATE = """# FRUSClaw local agent configuration
[agent]
mode = "research"
allowed_users = []
scheduler_interval_seconds = 30
"""

DEFAULT_ENV_TEMPLATE = """# FRUSClaw example environment variables
FRUSCLAW_DATA_DIR=.frusclaw
FRUSCLAW_DB_PATH=.frusclaw/frusclaw.sqlite3
FRUSCLAW_REPO_DIR=.frusclaw/frus
FRUSCLAW_MODE=research
TELEGRAM_BOT_TOKEN=
FRUSCLAW_ALLOWED_USERS=
TELEGRAM_POLL_INTERVAL=30
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
WHATSAPP_API_VERSION=v20.0
WHATSAPP_WEBHOOK_HOST=127.0.0.1
WHATSAPP_WEBHOOK_PORT=8000
"""


def ensure_local_config_files(config: AppConfig) -> None:
    """Write default local config scaffolding if it does not exist yet."""
    config.ensure_directories()
    if not config.config_path.exists():
        config.config_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    if not config.env_example_path.exists():
        config.env_example_path.write_text(DEFAULT_ENV_TEMPLATE, encoding="utf-8")


def load_agent_settings(config_path: Path) -> AgentSettings:
    """Load agent settings from local TOML and process environment."""
    config_data: dict[str, object] = {}
    if config_path.exists():
        config_data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    agent_data = _as_dict(config_data.get("agent"))
    mode = os.environ.get("FRUSCLAW_MODE", str(agent_data.get("mode", "research")))
    allowed_users = _parse_allowlist(os.environ.get("FRUSCLAW_ALLOWED_USERS")) or list(
        agent_data.get("allowed_users", [])
    )

    return AgentSettings(
        mode=mode,
        allowed_users=allowed_users,
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_poll_interval_seconds=int(os.environ.get("TELEGRAM_POLL_INTERVAL", "30")),
        whatsapp_access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
        whatsapp_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
        whatsapp_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
        whatsapp_app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
        whatsapp_api_version=os.environ.get("WHATSAPP_API_VERSION", "v20.0"),
        whatsapp_webhook_host=os.environ.get("WHATSAPP_WEBHOOK_HOST", "127.0.0.1"),
        whatsapp_webhook_port=int(os.environ.get("WHATSAPP_WEBHOOK_PORT", "8000")),
        scheduler_interval_seconds=int(agent_data.get("scheduler_interval_seconds", 30)),
    )


def _parse_allowlist(value: str | None) -> list[str]:
    """Parse a comma-separated allowlist."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_dict(value: object) -> dict[str, object]:
    """Normalize TOML sections to dictionaries."""
    return value if isinstance(value, dict) else {}
