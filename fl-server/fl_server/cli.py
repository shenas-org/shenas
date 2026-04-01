"""CLI entry point for the shenas FL server."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

app = typer.Typer(name="shenas-fl", help="Shenas federated learning coordinator.")


@app.command("serve")
def serve(
    task: str = typer.Option("sleep-forecast", help="Task to run"),
    grpc_host: str = typer.Option("0.0.0.0", help="Flower gRPC bind address"),
    grpc_port: int = typer.Option(8080, help="Flower gRPC port"),
    api_host: str = typer.Option("0.0.0.0", help="REST API bind address"),
    api_port: int = typer.Option(8081, help="REST API port"),
    weights_dir: Path = typer.Option(Path(".shenas-fl/weights"), help="Directory for model weights"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Start the FL coordinator (Flower server + REST API)."""
    import uvicorn

    from fl_server.models import ModelStore
    from fl_server.server import api as fastapi_app
    from fl_server.server import start_fl_server_background

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from fl_server.auth import ClientRegistry

    store = ModelStore(weights_dir=weights_dir)
    fastapi_app.state.store = store
    fastapi_app.state.registry = ClientRegistry()

    grpc_address = f"{grpc_host}:{grpc_port}"
    typer.echo(f"Starting FL server for task '{task}' on {grpc_address}")
    typer.echo(f"REST API on http://{api_host}:{api_port}")

    start_fl_server_background(task, grpc_address=grpc_address, weights_dir=weights_dir)

    uvicorn.run(fastapi_app, host=api_host, port=api_port)


@app.command("register")
def register_cmd(
    name: str = typer.Argument(help="Client name to register"),
) -> None:
    """Register a new FL client and print its auth token."""
    from fl_server.auth import ClientRegistry

    registry = ClientRegistry()
    token = registry.register(name)
    typer.echo(f"Client: {name}")
    typer.echo(f"Token:  {token}")
    typer.echo("\nStore this token securely -- it cannot be retrieved again.")


@app.command("clients")
def clients_cmd() -> None:
    """List registered FL clients."""
    from fl_server.auth import ClientRegistry

    registry = ClientRegistry()
    clients = registry.list_clients()
    if not clients:
        typer.echo("No clients registered")
        return
    for name in clients:
        typer.echo(f"  {name}")


@app.command("tasks")
def list_tasks_cmd() -> None:
    """List available FL tasks."""
    from rich.console import Console
    from rich.table import Table

    from fl_server.tasks import list_tasks

    tasks = list_tasks()
    if not tasks:
        typer.echo("No tasks defined")
        return

    console = Console()
    table = Table()
    table.add_column("Name", style="green")
    table.add_column("Model")
    table.add_column("Features")
    table.add_column("Target")
    table.add_column("Rounds", justify="right")
    table.add_column("Min clients", justify="right")

    for t in tasks:
        table.add_row(t.name, t.model, ", ".join(t.features), t.target, str(t.num_rounds), str(t.min_clients))

    console.print(table)
