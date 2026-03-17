"""Agent config, scheduler, brief, channel, and lifecycle tests for FRUSClaw."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from frusclaw_agent.actions import FrusResearchService
from frusclaw_agent.agent import get_agent_status, start_agent, stop_agent
from frusclaw_agent.channels.base import ChannelEnvelope
from frusclaw_agent.channels.telegram import DENIAL_MESSAGE, TelegramChannelAdapter
from frusclaw_agent.channels.whatsapp import WhatsAppChannelAdapter
from frusclaw_agent.config import ensure_local_config_files, load_agent_settings
from frusclaw_agent.scheduler import AgentScheduler
from frusclaw_cli.main import app
from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.indexer import build_index


SAMPLE_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="frus-test-volume">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Foreign Relations of the United States, Test Volume</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="document" xml:id="doc-1">
        <head>Memorandum of Conversation</head>
        <p>The Berlin crisis remained central to the discussion.</p>
      </div>
      <div type="document" xml:id="doc-2">
        <head>Telegram From Bonn</head>
        <p>Officials discussed trade policy and alliance strategy.</p>
      </div>
      <div type="document" xml:id="doc-3">
        <head>Briefing Memorandum on Berlin</head>
        <p>Berlin planning focused on allied coordination and negotiations.</p>
      </div>
    </body>
  </text>
</TEI>
"""


@dataclass
class FakeProcess:
    """Simple stand-in for a spawned background process."""

    pid: int


class DummyHTTPResponse:
    """Tiny response stub for outbound WhatsApp tests."""

    def __init__(self, body: str) -> None:
        self.body = body

    def __enter__(self) -> "DummyHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def read(self) -> bytes:
        return self.body.encode("utf-8")


runner = CliRunner()


def test_config_loading_merges_config_and_environment(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    config.config_path.write_text(
        """
        [agent]
        mode = "public"
        allowed_users = ["alice"]
        scheduler_interval_seconds = 15
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("FRUSCLAW_MODE", "research")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "alice,bob")
    monkeypatch.setenv("FRUSCLAW_DATA_DIR", str(tmp_path / ".frusclaw"))
    monkeypatch.setenv("FRUSCLAW_DB_PATH", str(tmp_path / ".frusclaw" / "frusclaw.sqlite3"))
    monkeypatch.setenv("FRUSCLAW_REPO_DIR", str(tmp_path / ".frusclaw" / "frus"))

    resolved = AppConfig.from_paths()
    settings = load_agent_settings(config.config_path)

    assert resolved.data_dir == (tmp_path / ".frusclaw").resolve()
    assert resolved.db_path == (tmp_path / ".frusclaw" / "frusclaw.sqlite3").resolve()
    assert resolved.repo_dir == (tmp_path / ".frusclaw" / "frus").resolve()
    assert settings.mode == "research"
    assert settings.scheduler_interval_seconds == 15
    assert settings.telegram_bot_token == "test-token"
    assert settings.allowed_users == ["alice", "bob"]


def test_setup_command_creates_local_scaffolding(tmp_path: Path) -> None:
    data_dir = tmp_path / ".frusclaw"

    result = runner.invoke(app, ["setup", "--data-dir", str(data_dir)])

    assert result.exit_code == 0
    assert data_dir.exists()
    assert (data_dir / "config.toml").exists()
    assert (data_dir / ".env.example").exists()
    assert "frusclaw sync" in result.stdout
    assert "frusclaw index" in result.stdout
    assert "frusclaw agent start" in result.stdout


def test_job_creation_and_recurring_persistence(tmp_path: Path) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    config.ensure_directories()
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    now = datetime(2026, 3, 17, 7, 30, tzinfo=UTC)

    once_job = scheduler.create_one_time_brief_job(topic="Berlin", mode="public", run_at=now)
    daily_job = scheduler.create_daily_brief_job(topic="Bonn", now=now)
    weekly_job = scheduler.create_weekly_brief_job(topic="Moscow", now=now)

    jobs = scheduler.list_jobs()

    assert [job.cadence for job in jobs] == ["once", "daily", "weekly"]
    assert jobs[0].job_id == once_job.job_id
    assert jobs[1].job_id == daily_job.job_id
    assert jobs[2].job_id == weekly_job.job_id
    assert datetime.fromisoformat(daily_job.next_run_at) > now
    assert datetime.fromisoformat(weekly_job.next_run_at) > datetime.fromisoformat(daily_job.next_run_at)


def test_daily_brief_generation_uses_search_results(tmp_path: Path) -> None:
    config = _build_indexed_config(tmp_path)
    service = FrusResearchService(config.db_path)

    public_brief = service.daily_brief("Berlin", mode="public")
    research_brief = service.daily_brief("Berlin", mode="research")

    assert "Brief for 'Berlin':" in public_brief
    assert "Memorandum of Conversation" in public_brief
    assert "Research brief for 'Berlin':" in research_brief
    assert "doc-1 [frus-test-volume]" in research_brief


def test_job_removal_deletes_persisted_job(tmp_path: Path) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    config.ensure_directories()
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    job = scheduler.create_daily_brief_job(topic="Berlin")

    removed = scheduler.remove_job(job.job_id)
    jobs = scheduler.list_jobs()

    assert removed is True
    assert jobs == []


def test_jobs_remove_command_removes_job(tmp_path: Path) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    config.ensure_directories()
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    job = scheduler.create_weekly_brief_job(topic="Berlin")

    result = runner.invoke(app, ["jobs", "remove", str(job.job_id), "--data-dir", str(config.data_dir)])

    assert result.exit_code == 0
    assert f"jobs: removed job {job.job_id}" in result.stdout
    assert scheduler.list_jobs() == []


def test_agent_status_reports_not_running_when_state_is_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / ".frusclaw"

    result = runner.invoke(app, ["agent", "status", "--data-dir", str(data_dir)])

    assert result.exit_code == 0
    assert "agent: status=stopped" in result.stdout
    assert "agent is not running" in result.stdout


def test_agent_start_and_status_use_local_state_file(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)

    monkeypatch.setattr("frusclaw_agent.agent._is_process_running", lambda pid: pid == 4321)

    status = start_agent(config, spawner=lambda _config: FakeProcess(pid=4321))
    current = get_agent_status(config)

    assert status.status == "starting"
    assert status.pid == 4321
    assert current.running is True
    assert current.pid == 4321
    assert config.agent_pid_path.exists()


def test_duplicate_start_returns_existing_running_status(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()

    monkeypatch.setattr("frusclaw_agent.agent._is_process_running", lambda pid: pid == 4321)

    first = start_agent(config, spawner=lambda _config: FakeProcess(pid=4321))
    second = start_agent(config, spawner=lambda _config: FakeProcess(pid=9999))

    assert first.pid == 4321
    assert second.pid == 4321
    assert second.message == "agent is already running"


def test_stop_flow_clears_pid_and_state_files(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    running = {"active": True}

    def fake_is_process_running(pid: int) -> bool:
        return running["active"] and pid == 4321

    def fake_kill(pid: int, _sig: int) -> None:
        if pid == 4321:
            running["active"] = False

    monkeypatch.setattr("frusclaw_agent.agent._is_process_running", fake_is_process_running)
    monkeypatch.setattr("frusclaw_agent.agent.os.kill", fake_kill)

    start_agent(config, spawner=lambda _config: FakeProcess(pid=4321))
    stopped = stop_agent(config)

    assert stopped.running is False
    assert stopped.status == "stopped"
    assert not config.agent_pid_path.exists()
    assert not config.agent_state_path.exists()


def test_agent_cli_start_status_stop_flow(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    running = {"active": False}

    def fake_spawn(_config: AppConfig) -> FakeProcess:
        running["active"] = True
        return FakeProcess(pid=4321)

    def fake_is_process_running(pid: int) -> bool:
        return running["active"] and pid == 4321

    def fake_kill(pid: int, _sig: int) -> None:
        if pid == 4321:
            running["active"] = False

    monkeypatch.setattr("frusclaw_agent.agent._spawn_process", fake_spawn)
    monkeypatch.setattr("frusclaw_agent.agent._is_process_running", fake_is_process_running)
    monkeypatch.setattr("frusclaw_agent.agent.os.kill", fake_kill)

    started = runner.invoke(app, ["agent", "start", "--data-dir", str(config.data_dir)])
    status = runner.invoke(app, ["agent", "status", "--data-dir", str(config.data_dir)])
    stopped = runner.invoke(app, ["agent", "stop", "--data-dir", str(config.data_dir)])

    assert started.exit_code == 0
    assert "agent: status=starting" in started.stdout
    assert status.exit_code == 0
    assert "agent: status=starting" in status.stdout or "agent: status=running" in status.stdout
    assert stopped.exit_code == 0
    assert "agent: status=stopped" in stopped.stdout


def test_agent_status_reports_loaded_scheduled_jobs_and_telegram_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    scheduler.create_daily_brief_job(topic="Berlin")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "alice")
    monkeypatch.setattr("frusclaw_agent.agent._is_process_running", lambda pid: pid == 4321)
    config.agent_pid_path.write_text("4321\n", encoding="utf-8")
    config.agent_state_path.write_text(
        json.dumps(
            {
                "status": "running",
                "running": True,
                "pid": 4321,
                "message": "agent loop running in research mode",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["agent", "status", "--data-dir", str(config.data_dir)])

    assert result.exit_code == 0
    assert "agent: scheduled jobs active=True" in result.stdout
    assert "agent: scheduled job count=1" in result.stdout
    assert "agent: telegram configured=True" in result.stdout


def test_telegram_config_validation_reports_missing_values(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("FRUSCLAW_ALLOWED_USERS", raising=False)
    adapter = TelegramChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))

    errors = adapter.validate_config()

    assert "missing TELEGRAM_BOT_TOKEN" in errors
    assert "missing FRUSCLAW_ALLOWED_USERS" in errors


def test_telegram_allowlist_enforcement_returns_denial_for_unknown_user(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_indexed_config(tmp_path)
    ensure_local_config_files(config)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "alice")
    adapter = TelegramChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))

    denied = adapter.handle_message(ChannelEnvelope(user_id="mallory", text="search Berlin"))
    allowed = adapter.handle_message(ChannelEnvelope(user_id="alice", text="search Berlin"))

    assert denied.ok is False
    assert denied.text == DENIAL_MESSAGE
    assert allowed.ok is True
    assert "Search results for 'Berlin':" in allowed.text


def test_telegram_adapter_initializes_from_config_path(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "alice,bob")
    monkeypatch.setenv("TELEGRAM_POLL_INTERVAL", "45")

    adapter = TelegramChannelAdapter.from_config_path(
        config.config_path,
        FrusResearchService(config.db_path),
    )
    status = adapter.status()

    assert status.valid is True
    assert status.allowed_user_count == 2
    assert status.poll_interval_seconds == 45


def test_whatsapp_config_validation_reports_missing_values(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)
    monkeypatch.delenv("FRUSCLAW_ALLOWED_USERS", raising=False)
    adapter = WhatsAppChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))

    errors = adapter.validate_config()

    assert "missing WHATSAPP_ACCESS_TOKEN" in errors
    assert "missing WHATSAPP_PHONE_NUMBER_ID" in errors
    assert "missing WHATSAPP_VERIFY_TOKEN" in errors
    assert "missing FRUSCLAW_ALLOWED_USERS" in errors


def test_whatsapp_webhook_verification_handling(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    adapter = WhatsAppChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))

    ok_status, ok_body = adapter.verify_webhook("subscribe", "verify-me", "12345")
    denied_status, denied_body = adapter.verify_webhook("subscribe", "wrong", "12345")

    assert ok_status == 200
    assert ok_body == "12345"
    assert denied_status == 403
    assert denied_body == "forbidden"


def test_whatsapp_inbound_message_parsing(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "15551234567")
    adapter = WhatsAppChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.1",
                                    "type": "text",
                                    "text": {"body": "search Berlin"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    messages = adapter.parse_incoming_messages(payload)

    assert len(messages) == 1
    assert messages[0].from_user == "15551234567"
    assert messages[0].text == "search Berlin"
    assert messages[0].message_id == "wamid.1"


def test_whatsapp_allowlist_enforcement_returns_denial_for_unknown_phone(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_indexed_config(tmp_path)
    ensure_local_config_files(config)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "15551234567")
    adapter = WhatsAppChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))

    denied = adapter.handle_message(ChannelEnvelope(user_id="19998887777", text="search Berlin"))
    allowed = adapter.handle_message(ChannelEnvelope(user_id="15551234567", text="search Berlin"))

    assert denied.ok is False
    assert denied.text == DENIAL_MESSAGE
    assert allowed.ok is True
    assert "Search results for 'Berlin':" in allowed.text


def test_whatsapp_outbound_payload_construction_and_send(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    ensure_local_config_files(config)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-id")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "15551234567")
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        captured["url"] = req.full_url
        captured["body"] = req.data.decode("utf-8")
        captured["auth"] = req.headers.get("Authorization")
        return DummyHTTPResponse('{"messages":[{"id":"mid"}]}')

    adapter = WhatsAppChannelAdapter(
        load_agent_settings(config.config_path),
        FrusResearchService(config.db_path),
        urlopen=fake_urlopen,
    )

    payload = adapter.outbound_payload("15551234567", "hello")
    ok, response = adapter.send_text("15551234567", "hello")

    assert payload["to"] == "15551234567"
    assert payload["text"]["body"] == "hello"
    assert ok is True
    assert "messages" in response
    assert captured["url"] == "https://graph.facebook.com/v20.0/phone-id/messages"
    assert "Bearer token" == captured["auth"]


def test_whatsapp_message_routes_to_existing_frus_actions(tmp_path: Path, monkeypatch) -> None:
    config = _build_indexed_config(tmp_path)
    ensure_local_config_files(config)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify")
    monkeypatch.setenv("FRUSCLAW_ALLOWED_USERS", "15551234567")
    adapter = WhatsAppChannelAdapter(load_agent_settings(config.config_path), FrusResearchService(config.db_path))
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.2",
                                    "type": "text",
                                    "text": {"body": "doc doc-1"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    results = adapter.process_webhook_payload(payload)

    assert len(results) == 1
    assert results[0].ok is True
    assert "Document doc-1" in results[0].text


def _build_indexed_config(tmp_path: Path) -> AppConfig:
    config = AppConfig.from_paths(data_dir=tmp_path / ".frusclaw")
    volumes_dir = config.repo_dir / "volumes"
    volumes_dir.mkdir(parents=True, exist_ok=True)
    (volumes_dir / "test-volume.xml").write_text(SAMPLE_TEI, encoding="utf-8")
    build_index(config)
    return config
