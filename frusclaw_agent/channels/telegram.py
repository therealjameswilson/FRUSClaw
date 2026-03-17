"""Telegram-first channel scaffold for FRUSClaw."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frusclaw_agent.actions import FrusResearchService, FrusSkillProvider
from frusclaw_agent.channels.base import BaseChannelAdapter, ChannelEnvelope, ChannelResult
from frusclaw_agent.config import load_agent_settings
from frusclaw_agent.models import AgentSettings
from frusclaw_agent.providers import ChannelMessage


DENIAL_MESSAGE = "Access denied. This FRUSClaw instance only accepts approved users."


@dataclass(slots=True)
class TelegramAdapterStatus:
    """Validation summary for the Telegram scaffold."""

    valid: bool
    errors: list[str]
    allowed_user_count: int
    poll_interval_seconds: int


class TelegramChannelAdapter(BaseChannelAdapter):
    """Config-validating Telegram scaffold without full polling support."""

    def __init__(self, settings: AgentSettings, service: FrusResearchService) -> None:
        self.settings = settings
        self.service = service
        self.skill = FrusSkillProvider(service)

    @classmethod
    def from_config_path(
        cls,
        config_path: Path,
        service: FrusResearchService,
    ) -> "TelegramChannelAdapter":
        """Build an adapter from the local FRUSClaw config path."""
        return cls(load_agent_settings(config_path), service)

    def validate_config(self) -> list[str]:
        """Return Telegram scaffold config errors."""
        errors: list[str] = []
        if not self.settings.telegram_bot_token.strip():
            errors.append("missing TELEGRAM_BOT_TOKEN")
        if not self.settings.allowed_users:
            errors.append("missing FRUSCLAW_ALLOWED_USERS")
        if self.settings.telegram_poll_interval_seconds <= 0:
            errors.append("TELEGRAM_POLL_INTERVAL must be greater than 0")
        return errors

    def status(self) -> TelegramAdapterStatus:
        """Return a summary of current adapter readiness."""
        errors = self.validate_config()
        return TelegramAdapterStatus(
            valid=not errors,
            errors=errors,
            allowed_user_count=len(self.settings.allowed_users),
            poll_interval_seconds=self.settings.telegram_poll_interval_seconds,
        )

    def is_allowed_user(self, user_id: str) -> bool:
        """Return whether a Telegram user is allowlisted."""
        return user_id in self.settings.allowed_users

    def handle_message(self, envelope: ChannelEnvelope) -> ChannelResult:
        """Route one Telegram-style message through existing FRUS actions."""
        if not self.is_allowed_user(envelope.user_id):
            return ChannelResult(ok=False, text=DENIAL_MESSAGE)

        response = self.skill.handle(
            ChannelMessage(
                channel="telegram",
                user_id=envelope.user_id,
                text=envelope.text,
                mode=envelope.mode,
            )
        )
        return ChannelResult(ok=True, text=response)

    def run(self) -> str:
        """Return a scaffold run message after config validation."""
        errors = self.validate_config()
        if errors:
            raise RuntimeError("; ".join(errors))
        return (
            "telegram: scaffold ready "
            f"(poll_interval={self.settings.telegram_poll_interval_seconds}s, "
            f"allowed_users={len(self.settings.allowed_users)})"
        )
