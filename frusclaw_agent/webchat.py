"""WebChat placeholder for a future FRUSClaw local channel."""

from __future__ import annotations


class WebChatChannelProvider:
    """Config-only placeholder for future local chat support."""

    name = "webchat"

    def start(self) -> None:
        """No-op placeholder."""
        return None

    def stop(self) -> None:
        """No-op placeholder."""
        return None
