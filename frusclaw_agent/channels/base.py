"""Base channel abstractions for FRUSClaw."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ChannelEnvelope:
    """Normalized inbound channel message."""

    user_id: str
    text: str
    mode: str = "public"


@dataclass(slots=True)
class ChannelResult:
    """Normalized outbound channel response."""

    ok: bool
    text: str


class BaseChannelAdapter(ABC):
    """Minimal interface for FRUSClaw message channels."""

    @abstractmethod
    def validate_config(self) -> list[str]:
        """Return configuration validation errors."""

    @abstractmethod
    def handle_message(self, envelope: ChannelEnvelope) -> ChannelResult:
        """Return a channel response for one inbound message."""
