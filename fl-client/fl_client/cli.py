"""CLI entry point for the shenas FL client daemon."""

from __future__ import annotations

import logging

import typer

app = typer.Typer(name="shenas-fl-client", help="Shenas federated learning client.")


@app.command("join")
def join(
    task: str = typer.Option("sleep-forecast", help="FL task to participate in"),
    fl_server: str = typer.Option("127.0.0.1:8080", help="Flower server address (gRPC)"),
    fl_api: str = typer.Option("http://127.0.0.1:8081", help="FL server REST API URL"),
    shenas_url: str = typer.Option("http://localhost:7280", help="Local shenas server URL"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Join a federated learning round as a client."""
    import flwr as fl

    from fl_client.client import ShenasClient

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    typer.echo(f"Joining FL task '{task}' at {fl_server}")
    typer.echo(f"Local data from {shenas_url}")

    client = ShenasClient(
        fl_api_url=fl_api,
        task_name=task,
        shenas_url=shenas_url,
    )

    fl.client.start_client(
        server_address=fl_server,
        client=client.to_client(),
    )

    typer.echo("FL round complete")
