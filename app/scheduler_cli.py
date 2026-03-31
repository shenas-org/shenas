"""CLI entry point for the shenas-scheduler sidecar."""

from __future__ import annotations

import logging

import typer

app = typer.Typer(name="shenas-scheduler", help="Background sync scheduler sidecar.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    server_url: str = typer.Option("http://localhost:7280", help="Shenas server URL"),
    check_interval: int = typer.Option(60, help="Seconds between schedule checks"),
    log_level: str = typer.Option("INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)"),
) -> None:
    """Run the background sync scheduler.

    Polls the shenas server for pipes due to sync and triggers them via REST.
    """
    if ctx.invoked_subcommand is not None:
        return

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    from app.sync_scheduler import run_daemon

    run_daemon(server_url=server_url, check_interval=check_interval)
