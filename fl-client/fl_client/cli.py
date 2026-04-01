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


@app.command("serve")
def serve(
    fl_api: str = typer.Option("http://127.0.0.1:8081", help="FL server REST API URL"),
    shenas_url: str = typer.Option("http://localhost:7280", help="Local shenas server URL"),
    host: str = typer.Option("127.0.0.1", help="Inference API bind address"),
    port: int = typer.Option(8082, help="Inference API port"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Start the local inference API server."""
    import uvicorn

    from fl_client.api import api as inference_api
    from fl_client.inference import InferenceEngine

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    inference_api.state.engine = InferenceEngine(fl_api_url=fl_api, shenas_url=shenas_url)

    typer.echo(f"Inference API on http://{host}:{port}")
    uvicorn.run(inference_api, host=host, port=port)


@app.command("predict")
def predict_cmd(
    task: str = typer.Option("sleep-forecast", help="Task to predict"),
    fl_api: str = typer.Option("http://127.0.0.1:8081", help="FL server REST API URL"),
    shenas_url: str = typer.Option("http://localhost:7280", help="Local shenas server URL"),
) -> None:
    """Run a one-shot prediction and print results."""
    from rich.console import Console
    from rich.table import Table

    from fl_client.inference import InferenceEngine

    console = Console()
    engine = InferenceEngine(fl_api_url=fl_api, shenas_url=shenas_url)
    result = engine.predict(task)

    if result is None:
        console.print("[dim]No trained model available[/dim]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{task}[/bold] (round {result['round']}, {result['n_samples']} samples)")
    console.print(f"MAE: {result['mae']:.2f}\n")

    table = Table()
    table.add_column("Actual", justify="right")
    table.add_column("Predicted", justify="right")
    for actual, pred in zip(result["actuals"], result["predictions"]):
        table.add_row(f"{actual:.1f}", f"{pred:.1f}")
    console.print(table)
