"""Telegram placeholder for a future FRUSClaw channel adapter."""

from __future__ import annotations


class TelegramChannelProvider:
    """Config-only placeholder for future Telegram support."""

    name = "telegram"

    def start(self) -> None:
        """No-op placeholder."""
        return None

    def stop(self) -> None:
        """No-op placeholder."""
        return None
