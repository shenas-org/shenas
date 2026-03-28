from importlib.metadata import entry_points

import typer
from rich.console import Console

console = Console()


def _find_sync_callback(pipe_app: typer.Typer):  # type: ignore[no-untyped-def]
    """Find the sync command's callback function from a pipe's typer app."""
    for cmd_info in pipe_app.registered_commands:
        cb = cmd_info.callback
        name = cmd_info.name or (getattr(cb, "__name__", None) if cb else None)
        if name == "sync" and cmd_info.callback:
            return cmd_info.callback
    return None


def _resolve_defaults(func):  # type: ignore[no-untyped-def]
    """Call a typer command function with its declared defaults resolved."""
    import inspect

    kwargs = {}
    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        default = param.default
        if isinstance(default, typer.models.OptionInfo):
            kwargs[param_name] = default.default
        elif isinstance(default, typer.models.ArgumentInfo):
            kwargs[param_name] = default.default
        elif default is not inspect.Parameter.empty:
            kwargs[param_name] = default
    return func(**kwargs)


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
            sync_fn = _find_sync_callback(pipe_app)
            if sync_fn is None:
                console.print(f"[dim]No sync command for {name}, skipping.[/dim]")
                continue
            _resolve_defaults(sync_fn)
        except SystemExit:
            pass
        except Exception as exc:
            console.print(f"[red]{name} sync failed:[/red] {exc}")
            failed.append(name)

    if failed:
        console.print(f"\n[red]Failed: {', '.join(failed)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]All syncs complete.[/green]")
