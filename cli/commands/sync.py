from importlib.metadata import entry_points

import typer
from rich.console import Console

console = Console()


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
            # Find the sync command in the pipe's typer app
            sync_cmd = None
            for cmd_info in pipe_app.registered_commands:
                if cmd_info.name == "sync" or (cmd_info.callback and cmd_info.callback.__name__ == "sync"):
                    sync_cmd = cmd_info.callback
                    break
            if sync_cmd is None:
                console.print(f"[dim]No sync command found for {name}, skipping.[/dim]")
                continue
            sync_cmd()
        except SystemExit:
            pass
        except Exception as exc:
            console.print(f"[red]{name} sync failed:[/red] {exc}")
            failed.append(name)

    if failed:
        console.print(f"\n[red]Failed: {', '.join(failed)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]All syncs complete.[/green]")
