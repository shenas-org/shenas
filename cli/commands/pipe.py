from importlib.metadata import entry_points

import typer
from rich.console import Console

from cli.client import ShenasClient, ShenasServerError
from cli.commands.pkg import DEFAULT_INDEX, install, list_packages, uninstall

console = Console()

app = typer.Typer(help="Pipeline commands.", invoke_without_command=True)

for _ep in entry_points(group="shenas.pipes"):
    app.add_typer(_ep.load(), name=_ep.name)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("sync")
def sync_all() -> None:
    """Sync all installed pipes."""
    try:
        for event in ShenasClient().sync_all():
            pipe = event.get("pipe", "")
            message = event.get("message", "")
            event_type = event.get("_event", "message")

            if event_type == "progress":
                console.print(f"\n[bold]--- {pipe} ---[/bold]")
                console.print(f"[dim]{message}[/dim]")
            elif event_type == "complete":
                if pipe:
                    console.print(f"[green]{pipe}: {message}[/green]")
                else:
                    console.print(f"\n[green]{message}[/green]")
            elif event_type == "error":
                if pipe:
                    console.print(f"[red]{pipe}: {message}[/red]")
                else:
                    console.print(f"\n[red]{message}[/red]")
                    raise typer.Exit(code=1)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_cmd() -> None:
    """List installed pipe packages."""
    list_packages("pipe")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Pipe names, e.g. 'garmin lunchmoney'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more pipe packages from the repository."""
    for name in names:
        install(name, "pipe", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Pipe names, e.g. 'garmin lunchmoney'"),
) -> None:
    """Remove one or more pipe packages."""
    for name in names:
        uninstall(name, "pipe")
