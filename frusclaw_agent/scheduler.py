"""SQLite-backed recurring job scheduler for FRUSClaw."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from frusclaw_agent.actions import FrusResearchService
from frusclaw_agent.models import ScheduledJob


CADENCE_ONCE = "once"
CADENCE_DAILY = "daily"
CADENCE_WEEKLY = "weekly"


class AgentScheduler:
    """Manage local scheduled jobs in SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        """Ensure scheduler tables exist."""
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    cadence TEXT NOT NULL,
                    next_run_at TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    last_output TEXT
                )
                """
            )
            connection.commit()

    def create_one_time_brief_job(
        self,
        topic: str,
        mode: str = "research",
        run_at: datetime | None = None,
    ) -> ScheduledJob:
        """Create a one-time brief job."""
        current_time = run_at or datetime.now(UTC)
        return self._create_job(topic=topic, mode=mode, cadence=CADENCE_ONCE, next_run_at=current_time)

    def create_daily_brief_job(
        self,
        topic: str,
        mode: str = "research",
        now: datetime | None = None,
    ) -> ScheduledJob:
        """Create a recurring daily brief job."""
        current_time = now or datetime.now(UTC)
        next_run_at = _next_daily_run(current_time)
        return self._create_job(topic=topic, mode=mode, cadence=CADENCE_DAILY, next_run_at=next_run_at)

    def create_weekly_brief_job(
        self,
        topic: str,
        mode: str = "research",
        now: datetime | None = None,
    ) -> ScheduledJob:
        """Create a recurring weekly brief job."""
        current_time = now or datetime.now(UTC)
        next_run_at = _next_weekly_run(current_time)
        return self._create_job(topic=topic, mode=mode, cadence=CADENCE_WEEKLY, next_run_at=next_run_at)

    def list_jobs(self) -> list[ScheduledJob]:
        """Return all scheduled jobs."""
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT job_id, action, topic, mode, cadence, next_run_at, enabled, last_run_at
                FROM scheduled_jobs
                ORDER BY job_id
                """
            ).fetchall()
        return [ScheduledJob(*row[:-2], enabled=bool(row[-2]), last_run_at=row[-1]) for row in rows]

    def active_job_count(self) -> int:
        """Return the number of enabled scheduled jobs."""
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM scheduled_jobs WHERE enabled = 1"
            ).fetchone()
        return int(row[0])

    def remove_job(self, job_id: int) -> bool:
        """Delete one scheduled job by ID."""
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            connection.commit()
        return cursor.rowcount > 0

    def run_pending(
        self,
        service: FrusResearchService,
        now: datetime | None = None,
    ) -> list[ScheduledJob]:
        """Run due jobs, persist output, and reschedule recurring work."""
        current_time = now or datetime.now(UTC)
        due_jobs = self._due_jobs(current_time)
        for job in due_jobs:
            output = service.daily_brief(job.topic, mode=job.mode)
            self._mark_job_ran(job, current_time=current_time, output=output)
        return due_jobs

    def _create_job(
        self,
        topic: str,
        mode: str,
        cadence: str,
        next_run_at: datetime,
    ) -> ScheduledJob:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO scheduled_jobs (action, topic, mode, cadence, next_run_at, enabled)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                ("daily_brief", topic, mode, cadence, next_run_at.isoformat()),
            )
            connection.commit()
            job_id = int(cursor.lastrowid)
        return ScheduledJob(
            job_id=job_id,
            action="daily_brief",
            topic=topic,
            mode=mode,
            cadence=cadence,
            next_run_at=next_run_at.isoformat(),
            enabled=True,
            last_run_at=None,
        )

    def _due_jobs(self, current_time: datetime) -> list[ScheduledJob]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT job_id, action, topic, mode, cadence, next_run_at, enabled, last_run_at
                FROM scheduled_jobs
                WHERE enabled = 1 AND next_run_at <= ?
                ORDER BY next_run_at
                """,
                (current_time.isoformat(),),
            ).fetchall()
        return [ScheduledJob(*row[:-2], enabled=bool(row[-2]), last_run_at=row[-1]) for row in rows]

    def _mark_job_ran(self, job: ScheduledJob, current_time: datetime, output: str) -> None:
        next_run_at, enabled = _reschedule(job.cadence, current_time)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE scheduled_jobs
                SET last_run_at = ?, last_output = ?, next_run_at = ?, enabled = ?
                WHERE job_id = ?
                """,
                (
                    current_time.isoformat(),
                    output,
                    next_run_at.isoformat(),
                    1 if enabled else 0,
                    job.job_id,
                ),
            )
            connection.commit()


def _next_daily_run(current_time: datetime) -> datetime:
    return (current_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)


def _next_weekly_run(current_time: datetime) -> datetime:
    return (current_time + timedelta(days=7)).replace(hour=8, minute=0, second=0, microsecond=0)


def _reschedule(cadence: str, current_time: datetime) -> tuple[datetime, bool]:
    if cadence == CADENCE_DAILY:
        return _next_daily_run(current_time), True
    if cadence == CADENCE_WEEKLY:
        return _next_weekly_run(current_time), True
    return current_time, False
