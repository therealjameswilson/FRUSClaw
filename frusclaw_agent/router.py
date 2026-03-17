"""Minimal message router for the FRUSClaw agent skeleton."""

from __future__ import annotations

from frusclaw_agent.models import RoutedMessage


class MessageRouter:
    """Keep a minimal routing seam for later channels and tools."""

    def route(self, message: RoutedMessage) -> str:
        """Return a placeholder routed response."""
        return f"router: received {message.text!r} in {message.mode} mode"
