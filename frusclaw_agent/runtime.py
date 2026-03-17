"""Compatibility wrappers around the Phase 3A agent skeleton."""

from __future__ import annotations

from frusclaw_agent.agent import get_agent_status, start_agent, stop_agent, update_agent_heartbeat
from frusclaw_agent.models import AgentStatus

__all__ = [
    "AgentStatus",
    "get_agent_status",
    "start_agent",
    "stop_agent",
    "update_agent_heartbeat",
]
