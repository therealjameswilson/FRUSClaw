"""Typer CLI entrypoint for FRUSClaw."""

from __future__ import annotations

from pathlib import Path

import typer

from frusclaw_agent.actions import FrusResearchService
from frusclaw_agent.agent import get_agent_status, start_agent, stop_agent
from frusclaw_agent.channels.telegram import TelegramChannelAdapter
from frusclaw_agent.channels.whatsapp import WhatsAppChannelAdapter
from frusclaw_agent.config import ensure_local_config_files, load_agent_settings
from frusclaw_agent.scheduler import AgentScheduler
from frusclaw_indexer.config import AppConfig
from frusclaw_indexer.database import IndexDatabase
from frusclaw_indexer.git_ops import ensure_frus_repository
from frusclaw_indexer.indexer import build_index
from frusclaw_indexer.render import render_search_results, render_stats
from frusclaw_indexer.search import search_documents

app = typer.Typer(
    help="Local-first research assistant for the FRUS series.",
    no_args_is_help=True,
)
agent_app = typer.Typer(help="Always-on local FRUSClaw agent controls.")
jobs_app = typer.Typer(help="Manage local recurring FRUSClaw jobs.")
telegram_app = typer.Typer(help="Telegram-first FRUSClaw channel scaffold.")
whatsapp_app = typer.Typer(help="WhatsApp Cloud API FRUSClaw channel scaffold.")
app.add_typer(agent_app, name="agent")
app.add_typer(jobs_app, name="jobs")
app.add_typer(telegram_app, name="telegram")
app.add_typer(whatsapp_app, name="whatsapp")


def _placeholder(command_name: str, detail: str) -> None:
    """Emit a consistent scaffold message for incomplete commands."""
    typer.echo(f"{command_name}: {detail}")


def _config_options(
    data_dir: Path | None = None,
    repo_dir: Path | None = None,
    db_path: Path | None = None,
) -> AppConfig:
    """Resolve command configuration from explicit paths or defaults."""
    return AppConfig.from_paths(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)


def _research_service(config: AppConfig) -> FrusResearchService:
    """Create a research service over the local FRUS index."""
    return FrusResearchService(config.db_path)


def _telegram_adapter(config: AppConfig) -> TelegramChannelAdapter:
    """Build the Telegram scaffold adapter."""
    return TelegramChannelAdapter(load_agent_settings(config.config_path), _research_service(config))


def _whatsapp_adapter(config: AppConfig) -> WhatsAppChannelAdapter:
    """Build the WhatsApp scaffold adapter."""
    return WhatsAppChannelAdapter(load_agent_settings(config.config_path), _research_service(config))


@app.command()
def init(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Initialize a local FRUSClaw workspace."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    config.ensure_directories()
    IndexDatabase(config.db_path).initialize()
    typer.echo(f"init: data directory={config.data_dir}")
    typer.echo(f"init: repository path={config.repo_dir}")
    typer.echo(f"init: database path={config.db_path}")


@app.command()
def setup(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Prepare local FRUSClaw config scaffolding and print next steps."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    config.ensure_directories()
    IndexDatabase(config.db_path).initialize()
    AgentScheduler(config.db_path).initialize()
    ensure_local_config_files(config)
    typer.echo(f"setup: data directory={config.data_dir}")
    typer.echo(f"setup: config path={config.config_path}")
    typer.echo(f"setup: env example path={config.env_example_path}")
    typer.echo(f"setup: database path={config.db_path}")
    typer.echo("setup: next steps")
    typer.echo("setup:   1. frusclaw sync")
    typer.echo("setup:   2. frusclaw index")
    typer.echo("setup:   3. frusclaw agent start")


@app.command()
def sync(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Prepare local FRUS data and sync the FRUS repository."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    try:
        result = ensure_frus_repository(config)
    except RuntimeError as error:
        typer.echo(f"sync: error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"sync: data directory={config.data_dir}")
    typer.echo(f"sync: repository path={result.repo_path}")
    typer.echo(f"sync: {result.message}")


@app.command()
def index(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Parse FRUS TEI volumes and populate the local SQLite index."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    try:
        summary = build_index(config)
    except RuntimeError as error:
        typer.echo(f"index: error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"index: volumes indexed={summary.volume_count}")
    typer.echo(f"index: documents indexed={summary.document_count}")
    typer.echo(f"index: database path={config.db_path}")


@app.command()
def search(
    query: str,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    limit: int = typer.Option(10, min=1, max=100, help="Maximum number of search results."),
) -> None:
    """Search headings and full text in the local SQLite index."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    results = search_documents(config.db_path, query=query, limit=limit)
    typer.echo(render_search_results(results))


@app.command("doc")
def doc_command(
    doc_id: str,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    mode: str = typer.Option("research", help="Response mode: public or research."),
) -> None:
    """Retrieve one indexed FRUS document."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    typer.echo(_research_service(config).document(document_id=doc_id, mode=mode))


@app.command()
def volume(
    volume_id: str,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    mode: str = typer.Option("research", help="Response mode: public or research."),
) -> None:
    """Retrieve one indexed FRUS volume."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    typer.echo(_research_service(config).volume(volume_id=volume_id, mode=mode))


@app.command("resolve-url")
def resolve_url(
    identifier: str,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    mode: str = typer.Option("research", help="Response mode: public or research."),
) -> None:
    """Resolve a best-effort history.state.gov URL for a FRUS identifier."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    typer.echo(_research_service(config).resolve_url(identifier=identifier, mode=mode))


@app.command()
def brief(
    topic: str = typer.Option(..., "--topic", help="Topic for the FRUS brief."),
    daily: bool = typer.Option(False, "--daily", help="Create a recurring daily brief job."),
    weekly: bool = typer.Option(False, "--weekly", help="Create a recurring weekly brief job."),
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
    mode: str = typer.Option("research", help="Response mode: public or research."),
) -> None:
    """Generate a one-off brief or schedule a recurring brief."""
    if daily and weekly:
        typer.echo("brief: error: choose either --daily or --weekly, not both", err=True)
        raise typer.Exit(code=1)

    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    if daily:
        job = scheduler.create_daily_brief_job(topic=topic, mode=mode)
        typer.echo(f"brief: scheduled daily brief job {job.job_id} for topic={job.topic!r}")
        typer.echo(f"brief: next run at {job.next_run_at}")
        return
    if weekly:
        job = scheduler.create_weekly_brief_job(topic=topic, mode=mode)
        typer.echo(f"brief: scheduled weekly brief job {job.job_id} for topic={job.topic!r}")
        typer.echo(f"brief: next run at {job.next_run_at}")
        return

    typer.echo(_research_service(config).daily_brief(topic=topic, mode=mode))


@app.command()
def stats(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Show basic local index information."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    typer.echo(render_stats(config))


@jobs_app.command("list")
def jobs_list(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """List scheduled local jobs."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    jobs = scheduler.list_jobs()
    if not jobs:
        typer.echo("jobs: no scheduled jobs")
        return
    typer.echo(f"jobs: {len(jobs)} scheduled")
    for job in jobs:
        typer.echo(
            f"- {job.job_id}: {job.action} topic={job.topic!r} cadence={job.cadence} "
            f"mode={job.mode} next_run_at={job.next_run_at}"
        )


@jobs_app.command("remove")
def jobs_remove(
    job_id: int,
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Remove one scheduled local job."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    scheduler = AgentScheduler(config.db_path)
    scheduler.initialize()
    if not scheduler.remove_job(job_id):
        typer.echo(f"jobs: error: no job found with id {job_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"jobs: removed job {job_id}")


@telegram_app.command("check-config")
def telegram_check_config(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Validate Telegram scaffold configuration."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _telegram_adapter(config)
    status = adapter.status()
    if not status.valid:
        for error in status.errors:
            typer.echo(f"telegram: error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo("telegram: configuration valid")
    typer.echo(f"telegram: allowed users={status.allowed_user_count}")
    typer.echo(f"telegram: poll interval={status.poll_interval_seconds}s")


@telegram_app.command("run")
def telegram_run(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Run the Telegram scaffold validation path."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _telegram_adapter(config)
    try:
        message = adapter.run()
    except RuntimeError as error:
        typer.echo(f"telegram: error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(message)
    typer.echo("telegram: inbound message handling is scaffolded but full polling is not implemented yet")


@whatsapp_app.command("check-config")
def whatsapp_check_config(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Validate WhatsApp scaffold configuration."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _whatsapp_adapter(config)
    status = adapter.status()
    if not status.valid:
        for error in status.errors:
            typer.echo(f"whatsapp: error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo("whatsapp: configuration valid")
    typer.echo(f"whatsapp: allowed users={status.allowed_user_count}")
    typer.echo(f"whatsapp: webhook={status.webhook_url}")
    typer.echo(f"whatsapp: api version={status.api_version}")


@whatsapp_app.command("status")
def whatsapp_status(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Show WhatsApp scaffold readiness."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _whatsapp_adapter(config)
    status = adapter.status()
    typer.echo(f"whatsapp: valid={status.valid}")
    typer.echo(f"whatsapp: allowed users={status.allowed_user_count}")
    typer.echo(f"whatsapp: webhook={status.webhook_url}")
    typer.echo(f"whatsapp: api version={status.api_version}")
    if status.errors:
        for error in status.errors:
            typer.echo(f"whatsapp: error: {error}")


@whatsapp_app.command("send-test")
def whatsapp_send_test(
    to: str = typer.Option(..., "--to", help="Destination phone number in international format."),
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Send a simple test WhatsApp text message."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _whatsapp_adapter(config)
    errors = adapter.validate_config()
    if errors:
        for error in errors:
            typer.echo(f"whatsapp: error: {error}", err=True)
        raise typer.Exit(code=1)
    ok, response = adapter.send_text(to, "FRUSClaw WhatsApp test message.")
    if not ok:
        typer.echo(f"whatsapp: send failed: {response}", err=True)
        raise typer.Exit(code=1)
    typer.echo("whatsapp: test message sent")
    typer.echo(response)


@whatsapp_app.command("webhook")
def whatsapp_webhook(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Run the local WhatsApp webhook listener."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    adapter = _whatsapp_adapter(config)
    errors = adapter.validate_config()
    if errors:
        for error in errors:
            typer.echo(f"whatsapp: error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        "whatsapp: starting local webhook listener "
        f"on {adapter.status().webhook_url}"
    )
    adapter.run_webhook_server()


@agent_app.command("start")
def agent_start(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Start the local FRUSClaw agent."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    ensure_local_config_files(config)
    AgentScheduler(config.db_path).initialize()
    status = start_agent(config)
    typer.echo(f"agent: status={status.status}")
    if status.pid is not None:
        typer.echo(f"agent: pid={status.pid}")
    typer.echo(f"agent: scheduled jobs active={status.scheduled_jobs_active}")
    typer.echo(f"agent: scheduled job count={status.scheduled_job_count}")
    typer.echo(f"agent: telegram configured={status.telegram_configured}")
    typer.echo(f"agent: log path={config.agent_log_path}")
    typer.echo(f"agent: {status.message}")


@agent_app.command("stop")
def agent_stop(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Stop the local FRUSClaw agent."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    status = stop_agent(config)
    typer.echo(f"agent: status={status.status}")
    typer.echo(f"agent: scheduled jobs active={status.scheduled_jobs_active}")
    typer.echo(f"agent: telegram configured={status.telegram_configured}")
    typer.echo(f"agent: {status.message}")


@agent_app.command("status")
def agent_status(
    data_dir: Path | None = typer.Option(None, help="Base directory for local FRUSClaw data."),
    repo_dir: Path | None = typer.Option(None, help="Path to the local FRUS Git clone."),
    db_path: Path | None = typer.Option(None, help="Path to the local SQLite database."),
) -> None:
    """Show local FRUSClaw agent status."""
    config = _config_options(data_dir=data_dir, repo_dir=repo_dir, db_path=db_path)
    settings = load_agent_settings(config.config_path)
    status = get_agent_status(config)
    typer.echo(f"agent: status={status.status}")
    if status.pid is not None:
        typer.echo(f"agent: pid={status.pid}")
    typer.echo(f"agent: message={status.message}")
    typer.echo(f"agent: mode={settings.mode}")
    typer.echo(f"agent: allowed users={len(settings.allowed_users)}")
    typer.echo(f"agent: scheduled jobs active={status.scheduled_jobs_active}")
    typer.echo(f"agent: scheduled job count={status.scheduled_job_count}")
    typer.echo(f"agent: telegram configured={status.telegram_configured}")
    typer.echo(f"agent: log path={config.agent_log_path}")


if __name__ == "__main__":
    app()
