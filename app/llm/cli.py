"""CLI commands for local LLM model management (shenasctl model ...)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn
from rich.table import Table

from app.llm.models import DEFAULT_MODEL, Model, ModelStore

app = typer.Typer(help="Local LLM model management.", invoke_without_command=True)
console = Console()


@app.command("download")
def download_cmd(
    name: str = typer.Option(DEFAULT_MODEL.filename, help="GGUF filename to save as"),
    url: str = typer.Option(DEFAULT_MODEL.url, help="URL to download from"),
) -> None:
    """Download a GGUF model into the local model store."""
    model = Model(filename=name, url=url)
    if model.exists:
        console.print(f"[yellow]Already exists:[/yellow] {model.path}")
        return

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    ) as progress:
        task = progress.add_task(f"Downloading {name}", total=None)

        def on_progress(done: int, total: int) -> None:
            if total:
                progress.update(task, completed=done, total=total)

        ModelStore.download(model, on_progress=on_progress)

    console.print(f"[green]Downloaded[/green] {model.path}")


@app.command("list")
def list_cmd() -> None:
    """List downloaded models."""
    models = ModelStore.list_models()
    if not models:
        console.print(f"[dim]No models found in {ModelStore.dir()}[/dim]")
        return

    table = Table(title="Local LLM Models")
    table.add_column("Filename")
    table.add_column("Size", justify="right")
    for m in models:
        table.add_row(m.filename, f"{m.size_bytes / 1e9:.2f} GB")
    console.print(table)


@app.command("remove")
def remove_cmd(name: str = typer.Argument(..., help="GGUF filename to remove")) -> None:
    """Remove a downloaded model."""
    model = Model(filename=name)
    if not model.exists:
        console.print(f"[red]Not found:[/red] {model.path}")
        raise typer.Exit(1)
    ModelStore.remove(name)
    console.print(f"[yellow]Removed[/yellow] {name}")


@app.command("path")
def path_cmd(name: str = typer.Argument(DEFAULT_MODEL.filename, help="GGUF filename")) -> None:
    """Print the absolute path to a model file."""
    typer.echo(str(ModelStore.resolve(name).path))
