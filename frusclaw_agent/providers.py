"""Provider interfaces for FRUSClaw channels and skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ChannelMessage:
    """Inbound message envelope for FRUSClaw channels."""

    channel: str
    user_id: str
    text: str
    mode: str = "public"


class ChannelProvider(ABC):
    """Abstract channel adapter interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    def start(self) -> None:
        """Start the provider."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the provider."""


class SkillProvider(ABC):
    """Abstract skill/action provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    def can_handle(self, message: ChannelMessage) -> bool:
        """Return whether this provider can handle a message."""

    @abstractmethod
    def handle(self, message: ChannelMessage) -> str:
        """Return a response for one inbound message."""
