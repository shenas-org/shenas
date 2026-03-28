from importlib.metadata import entry_points
from pathlib import Path

import typer

from cli.commands.pkg import DEFAULT_INDEX, install, list_packages, uninstall

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
    from rich.console import Console

    console = Console()
    failed = []
    for ep in sorted(entry_points(group="shenas.pipes"), key=lambda e: e.name):
        if ep.name == "core":
            continue
        console.print(f"\n[bold]--- {ep.name} ---[/bold]")
        try:
            pipe_app = ep.load()
            # Find and invoke the sync callback with resolved defaults
            for cmd in pipe_app.registered_commands:
                cmd_name = cmd.name or (getattr(cmd.callback, "__name__", None) if cmd.callback else None)
                if cmd_name == "sync" and cmd.callback:
                    import inspect

                    kwargs = {}
                    for p_name, p in inspect.signature(cmd.callback).parameters.items():
                        if isinstance(p.default, typer.models.OptionInfo):
                            kwargs[p_name] = p.default.default
                    cmd.callback(**kwargs)
                    break
        except SystemExit:
            pass
        except Exception as exc:
            console.print(f"[red]{ep.name} sync failed:[/red] {exc}")
            failed.append(ep.name)

    if failed:
        console.print(f"\n[red]Failed: {', '.join(failed)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]All syncs complete.[/green]")


@app.command("list")
def list_cmd() -> None:
    """List installed pipe packages."""
    list_packages("pipe")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Pipe names, e.g. 'garmin lunchmoney'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    public_key: Path = typer.Option(Path(".shenas/shenas.pub"), "--public-key", help="Path to Ed25519 public key"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more pipe packages from the repository."""
    for name in names:
        install(name, "pipe", index_url, public_key, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Pipe names, e.g. 'garmin lunchmoney'"),
) -> None:
    """Remove one or more pipe packages."""
    for name in names:
        uninstall(name, "pipe")
