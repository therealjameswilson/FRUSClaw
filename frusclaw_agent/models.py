"""Shared models for the FRUSClaw agent skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AgentSettings:
    """Merged local FRUSClaw agent settings."""

    mode: str = "research"
    allowed_users: list[str] = field(default_factory=list)
    telegram_bot_token: str = ""
    telegram_poll_interval_seconds: int = 30
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v20.0"
    whatsapp_webhook_host: str = "127.0.0.1"
    whatsapp_webhook_port: int = 8000
    scheduler_interval_seconds: int = 30


@dataclass(slots=True)
class AgentStatus:
    """Runtime status for the FRUSClaw local agent."""

    status: str
    running: bool
    pid: int | None
    message: str
    scheduled_jobs_active: bool = False
    scheduled_job_count: int = 0
    telegram_configured: bool = False


@dataclass(slots=True)
class ScheduledJob:
    """One scheduled FRUSClaw job."""

    job_id: int
    action: str
    topic: str
    mode: str
    cadence: str
    next_run_at: str
    enabled: bool
    last_run_at: str | None = None


@dataclass(slots=True)
class RoutedMessage:
    """Minimal routed message envelope."""

    text: str
    user_id: str = "local"
    mode: str = "public"
