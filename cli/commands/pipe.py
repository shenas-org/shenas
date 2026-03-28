"""Pipeline commands. Pipe subcommands (auth, sync) are proxied to the server."""

import typer
from rich.console import Console

from cli.client import ShenasClient, ShenasServerError
from cli.commands.pkg import DEFAULT_INDEX, install, uninstall

console = Console()

app = typer.Typer(help="Pipeline commands.", invoke_without_command=True)


def _register_pipe_commands() -> None:
    """Discover installed pipes from the server and register CLI subcommands."""
    try:
        client = ShenasClient()
        pipes = client.pipes_list()
    except (ShenasServerError, Exception):
        return

    for pipe_info in pipes:
        name = pipe_info["name"]
        commands = pipe_info.get("commands", [])
        pipe_app = typer.Typer(help=f"{name} pipe commands.", invoke_without_command=True)

        @pipe_app.callback()
        def _default(ctx: typer.Context) -> None:
            if ctx.invoked_subcommand is None:
                typer.echo(ctx.get_help())
                raise typer.Exit()

        has_sync = any(c["name"] == "sync" for c in commands)
        has_auth = any(c["name"] == "auth" for c in commands)

        if has_sync:
            _add_sync_command(pipe_app, name)
        if has_auth:
            _add_auth_command(pipe_app, name)

        app.add_typer(pipe_app, name=name)


def _add_sync_command(pipe_app: typer.Typer, pipe_name: str) -> None:
    @pipe_app.command("sync")
    def sync(
        start_date: str = typer.Option("30 days ago", help="Start date (YYYY-MM-DD or 'N days ago')"),
        full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop and re-download all data"),
    ) -> None:
        """Sync data from this pipe."""
        try:
            for event in ShenasClient().sync_pipe(pipe_name, start_date=start_date, full_refresh=full_refresh):
                message = event.get("message", "")
                event_type = event.get("_event", "message")

                if event_type == "progress":
                    console.print(f"[dim]{message}[/dim]")
                elif event_type == "complete":
                    console.print(f"[green]{message}[/green]")
                elif event_type == "error":
                    console.print(f"[red]{message}[/red]")
                    raise typer.Exit(code=1)
        except ShenasServerError as exc:
            console.print(f"[red]{exc.detail}[/red]")
            raise typer.Exit(code=1)


def _add_auth_command(pipe_app: typer.Typer, pipe_name: str) -> None:
    @pipe_app.command("auth")
    def auth() -> None:
        """Authenticate with this pipe's data source."""
        console.print(f"[yellow]Auth must be run locally: uv run shenasctl pipe {pipe_name} auth[/yellow]")
        raise typer.Exit(code=1)


# Try to register pipe subcommands from the server at import time.
# If the server is not running, only the static commands (sync, list, add, remove) are available.
_register_pipe_commands()


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
    """List installed pipes with their available commands."""
    from rich.table import Table

    try:
        pipes = ShenasClient().pipes_list()
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not pipes:
        console.print("[dim]No pipes installed[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("Pipe", style="green")
    table.add_column("Version", justify="right")
    table.add_column("Commands")
    for p in pipes:
        cmds = ", ".join(c["name"] for c in p.get("commands", []))
        table.add_row(p["name"], p.get("version", ""), cmds or "[dim]none[/dim]")
    console.print(table)


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
