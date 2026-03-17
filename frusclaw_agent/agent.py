"""Local FRUSClaw background agent lifecycle and loop."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from frusclaw_agent.actions import FrusResearchService
from frusclaw_agent.config import ensure_local_config_files, load_agent_settings
from frusclaw_agent.models import AgentStatus
from frusclaw_agent.scheduler import AgentScheduler
from frusclaw_indexer.config import AppConfig


def start_agent(
    config: AppConfig,
    spawner: Callable[[AppConfig], Any] | None = None,
) -> AgentStatus:
    """Launch the local agent process if it is not already running."""
    current = get_agent_status(config)
    if current.running:
        return AgentStatus(
            status="running",
            running=True,
            pid=current.pid,
            message="agent is already running",
            scheduled_jobs_active=current.scheduled_jobs_active,
            scheduled_job_count=current.scheduled_job_count,
            telegram_configured=current.telegram_configured,
        )

    ensure_local_config_files(config)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    spawn = spawner or _spawn_process
    process = spawn(config)
    _write_pid_file(config, process.pid)
    status = AgentStatus(
        status="starting",
        running=True,
        pid=process.pid,
        message="agent launch requested",
        scheduled_jobs_active=scheduler.active_job_count() > 0,
        scheduled_job_count=scheduler.active_job_count(),
        telegram_configured=_telegram_configured(config),
    )
    _write_state(config, status)
    _log(config, f"agent start requested pid={process.pid}")
    return status


def stop_agent(config: AppConfig) -> AgentStatus:
    """Stop the local background agent if it is running."""
    current = get_agent_status(config)
    if not current.running or current.pid is None:
        return AgentStatus(status="stopped", running=False, pid=None, message="agent is not running")

    try:
        os.kill(current.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    for _ in range(20):
        if not _is_process_running(current.pid):
            _clear_runtime_files(config)
            _log(config, "agent stopped")
            return AgentStatus(
                status="stopped",
                running=False,
                pid=None,
                message="agent stopped",
                scheduled_jobs_active=False,
                scheduled_job_count=0,
                telegram_configured=_telegram_configured(config),
            )
        time.sleep(0.1)

    return AgentStatus(
        status="stopping",
        running=True,
        pid=current.pid,
        message="stop signal sent; agent is still shutting down",
        scheduled_jobs_active=current.scheduled_jobs_active,
        scheduled_job_count=current.scheduled_job_count,
        telegram_configured=current.telegram_configured,
    )


def get_agent_status(config: AppConfig) -> AgentStatus:
    """Return the current local agent status."""
    config.ensure_directories()
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    scheduled_count = scheduler.active_job_count()
    telegram_configured = _telegram_configured(config)

    pid = _read_pid_file(config)
    if pid is None or not _is_process_running(pid):
        if pid is not None:
            _clear_runtime_files(config)
        return AgentStatus(
            status="stopped",
            running=False,
            pid=None,
            message="agent is not running",
            scheduled_jobs_active=scheduled_count > 0,
            scheduled_job_count=scheduled_count,
            telegram_configured=telegram_configured,
        )

    state: dict[str, object] = {}
    if config.agent_state_path.exists():
        state = json.loads(config.agent_state_path.read_text(encoding="utf-8"))

    return AgentStatus(
        status=str(state.get("status", "running")),
        running=True,
        pid=pid,
        message=str(state.get("message", "agent is running")),
        scheduled_jobs_active=scheduled_count > 0,
        scheduled_job_count=scheduled_count,
        telegram_configured=telegram_configured,
    )


def run_agent_loop(config: AppConfig) -> None:
    """Run the local background agent loop."""
    ensure_local_config_files(config)
    settings = load_agent_settings(config.config_path)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    service = FrusResearchService(config.db_path)

    running = True

    def _stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    _write_pid_file(config, os.getpid())
    _log(
        config,
        f"agent loop starting pid={os.getpid()} jobs={scheduler.active_job_count()} "
        f"telegram_configured={bool(settings.telegram_bot_token)}",
    )
    try:
        update_agent_heartbeat(
            config,
            message=f"agent loop running in {settings.mode} mode",
            scheduled_job_count=scheduler.active_job_count(),
        )
        while running:
            due_jobs = scheduler.run_pending(service)
            if due_jobs:
                _log(config, f"ran {len(due_jobs)} scheduled jobs")
            update_agent_heartbeat(
                config,
                message=f"agent loop running in {settings.mode} mode",
                scheduled_job_count=scheduler.active_job_count(),
            )
            time.sleep(settings.scheduler_interval_seconds)
    finally:
        _log(config, "agent loop shutting down cleanly")
        _clear_runtime_files(config)


def update_agent_heartbeat(config: AppConfig, message: str, scheduled_job_count: int) -> None:
    """Update local state from the background loop."""
    status = AgentStatus(
        status="running",
        running=True,
        pid=os.getpid(),
        message=message,
        scheduled_jobs_active=scheduled_job_count > 0,
        scheduled_job_count=scheduled_job_count,
        telegram_configured=_telegram_configured(config),
    )
    _write_state(config, status)


def main() -> None:
    """CLI entrypoint for the detached local agent process."""
    parser = argparse.ArgumentParser(description="Run the FRUSClaw local agent loop.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--repo-dir", required=True)
    parser.add_argument("--db-path", required=True)
    args = parser.parse_args()

    config = AppConfig.from_paths(
        data_dir=args.data_dir,
        repo_dir=args.repo_dir,
        db_path=args.db_path,
    )
    run_agent_loop(config)


def _write_state(config: AppConfig, status: AgentStatus) -> None:
    payload = asdict(status)
    payload["updated_at"] = datetime.now(UTC).isoformat()
    config.agent_state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_pid_file(config: AppConfig, pid: int) -> None:
    config.agent_pid_path.write_text(f"{pid}\n", encoding="utf-8")


def _read_pid_file(config: AppConfig) -> int | None:
    if not config.agent_pid_path.exists():
        return None
    try:
        return int(config.agent_pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _clear_runtime_files(config: AppConfig) -> None:
    if config.agent_pid_path.exists():
        config.agent_pid_path.unlink()
    if config.agent_state_path.exists():
        config.agent_state_path.unlink()


def _spawn_process(config: AppConfig) -> subprocess.Popen[bytes]:
    log_handle = config.agent_log_path.open("ab")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "frusclaw_agent.agent",
            "--data-dir",
            str(config.data_dir),
            "--repo-dir",
            str(config.repo_dir),
            "--db-path",
            str(config.db_path),
        ],
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _telegram_configured(config: AppConfig) -> bool:
    settings = load_agent_settings(config.config_path)
    return bool(settings.telegram_bot_token and settings.allowed_users)


def _log(config: AppConfig, message: str) -> None:
    timestamp = datetime.now(UTC).isoformat()
    config.agent_log_path.parent.mkdir(parents=True, exist_ok=True)
    with config.agent_log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


if __name__ == "__main__":
    main()
