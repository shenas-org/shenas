from importlib.metadata import entry_points

import typer
from rich.console import Console
from typer.testing import CliRunner

console = Console()
runner = CliRunner()


def sync_all() -> None:
    """Run sync for every installed pipe that has a sync command."""
    pipes = list(entry_points(group="shenas.pipes"))
    if not pipes:
        console.print("[dim]No pipes installed.[/dim]")
        return

    failed = []
    for ep in sorted(pipes, key=lambda e: e.name):
        name = ep.name
        if name == "core":
            continue
        console.print(f"\n[bold]--- {name} ---[/bold]")
        try:
            pipe_app = ep.load()
            # Invoke the sync command through typer so defaults resolve correctly
            tmp_app = typer.Typer()
            tmp_app.add_typer(pipe_app, name=name)
            result = runner.invoke(tmp_app, [name, "sync"])
            if result.output:
                console.print(result.output.rstrip())
            if result.exit_code != 0:
                failed.append(name)
        except Exception as exc:
            console.print(f"[red]{name} sync failed:[/red] {exc}")
            failed.append(name)

    if failed:
        console.print(f"\n[red]Failed: {', '.join(failed)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]All syncs complete.[/green]")
