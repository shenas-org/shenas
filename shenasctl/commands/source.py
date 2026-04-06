"""Sourceline commands. Source subcommands (auth, sync) are proxied to the server."""

from __future__ import annotations

import click
import typer
from rich.console import Console

from shenasctl.client import ShenasClient, ShenasServerError
from shenasctl.commands.plugin_cmd import DEFAULT_INDEX, install, uninstall

console = Console()


class _SourceGroup(typer.core.TyperGroup):
    """Custom group that shows a server error for unknown commands instead of the default error."""

    def resolve_command(self, ctx: click.Context, args: list[str]) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if not _server_available and args:
                console.print(
                    "[red]Cannot reach shenas server.[/red] Source commands require the server.\n"
                    "Start it with: [bold]shenas serve[/bold]"
                )
                raise SystemExit(1)
            raise


app = typer.Typer(help="Sourceline commands.", invoke_without_command=True, cls=_SourceGroup)


_server_available = False


def _register_pipe_commands() -> None:
    """Discover installed pipes from the server and register CLI subcommands.

    Uses the generic packages API, then adds pipe-specific commands
    (sync, auth, config) on top of the base describe command.
    """
    global _server_available
    try:
        client = ShenasClient()
        pipes = client.plugins_list("source")
        _server_available = True
    except Exception:
        return

    for pipe_info in pipes:
        name = pipe_info["name"]
        commands = set(pipe_info.get("commands", []))
        pipe_app = typer.Typer(help=f"{name} pipe commands.", invoke_without_command=True)

        @pipe_app.callback()
        def _default(ctx: typer.Context) -> None:
            if ctx.invoked_subcommand is None:
                typer.echo(ctx.get_help())
                raise typer.Exit

        if "describe" in commands:
            _add_info_command(pipe_app, name)
        if "sync" in commands:
            _add_sync_command(pipe_app, name)
        if "auth" in commands:
            _add_auth_command(pipe_app, name)
        if "config" in commands:
            _add_config_command(pipe_app, name)
        app.add_typer(pipe_app, name=name, rich_help_panel="Installed Sources")


def _add_info_command(pipe_app: typer.Typer, pipe_name: str) -> None:
    from shenasctl.commands.plugin_cmd import info as _info_plugin

    @pipe_app.command("info")
    def _info() -> None:
        """Show info about this pipe."""
        _info_plugin(pipe_name, "source")


def _add_sync_command(pipe_app: typer.Typer, pipe_name: str) -> None:
    @pipe_app.command("sync")
    def sync(
        start_date: str = typer.Option("30 days ago", help="Start date (YYYY-MM-DD or 'N days ago')"),
        full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop and re-download all data"),
        latest: int = typer.Option(0, "--latest", help="Only process N most recent items (0 = all)"),
        name_filter: str = typer.Option("", "--filter", help="Only process items matching this substring"),
        list_only: bool = typer.Option(False, "--list", help="List available items without processing"),
    ) -> None:
        """Sync data from this pipe."""
        extra: dict[str, str | int | bool] = {}
        if latest > 0:
            extra["latest"] = latest
        if name_filter:
            extra["name_filter"] = name_filter
        if list_only:
            extra["list_only"] = True
        try:
            for event in ShenasClient().sync_source(pipe_name, start_date=start_date, full_refresh=full_refresh, **extra):
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
        client = ShenasClient()

        # Fetch the credential fields this pipe needs
        try:
            auth_info = client.source_auth_fields(pipe_name)
        except ShenasServerError as exc:
            console.print(f"[red]{exc.detail}[/red]")
            raise typer.Exit(code=1)

        fields = auth_info.get("fields", [])
        instructions = auth_info.get("instructions", "")

        if instructions:
            console.print(f"\n{instructions}\n")

        # Collect credentials based on the pipe's declared fields
        credentials: dict[str, str] = {}
        for field in fields:
            value = typer.prompt(field["prompt"], hide_input=field.get("hide", False))
            credentials[field["name"]] = value

        if not fields:
            console.print("[dim]No credentials needed, starting auth flow...[/dim]")

        try:
            result = client.source_auth(pipe_name, credentials)
        except ShenasServerError as exc:
            console.print(f"[red]{exc.detail}[/red]")
            raise typer.Exit(code=1)

        # Handle MFA if needed
        if result.get("needs_mfa"):
            mfa_code = typer.prompt("MFA code")
            try:
                result = client.source_auth(pipe_name, {"mfa_code": mfa_code})
            except ShenasServerError as exc:
                console.print(f"[red]{exc.detail}[/red]")
                raise typer.Exit(code=1)

        # Handle OAuth URL (e.g. Gmail)
        if result.get("oauth_url"):
            import webbrowser

            url = result["oauth_url"]
            console.print(f"Open this URL to authorize:\n\n  [bold]{url}[/bold]\n")
            webbrowser.open(url)
            console.print("[dim]Waiting for authorization...[/dim]")
            try:
                result = client.source_auth(pipe_name, {"auth_complete": "true"})
            except ShenasServerError as exc:
                console.print(f"[red]{exc.detail}[/red]")
                raise typer.Exit(code=1)

        if result.get("ok"):
            console.print(f"[green]{result.get('message', 'Authenticated')}[/green]")
        else:
            console.print(f"[red]{result.get('error', 'Authentication failed')}[/red]")
            raise typer.Exit(code=1)


def _add_config_command(pipe_app: typer.Typer, pipe_name: str) -> None:
    @pipe_app.command("config")
    def config(
        key: str = typer.Argument(None, help="Config key to get/set"),
        value: str = typer.Argument(None, help="Value to set (omit to get current value)"),
    ) -> None:
        """View or set config for this pipe."""
        from rich.table import Table

        client = ShenasClient()
        kind = "source"

        if key and value:
            # Set a config value
            try:
                client.config_set(kind, pipe_name, key, value)
            except ShenasServerError as exc:
                console.print(f"[red]{exc.detail}[/red]")
                raise typer.Exit(code=1)
            console.print(f"[green]Set {kind} {pipe_name}.{key}[/green]")
        elif key:
            # Get a single value
            try:
                result = client.config_get(kind, pipe_name, key)
            except ShenasServerError as exc:
                if exc.status_code == 404:
                    console.print(f"[dim]Not set: {pipe_name}.{key}[/dim]")
                    raise typer.Exit(code=1)
                console.print(f"[red]{exc.detail}[/red]")
                raise typer.Exit(code=1)
            console.print(result["value"])
        else:
            # List all config
            try:
                configs = client.config_list(kind=kind, name=pipe_name)
            except ShenasServerError as exc:
                console.print(f"[red]{exc.detail}[/red]")
                raise typer.Exit(code=1)
            if not configs:
                console.print(f"[dim]No config for {pipe_name}[/dim]")
                return
            for cfg in configs:
                table = Table(title=f"[bold]{pipe_name} config[/bold]", show_lines=False)
                table.add_column("Key", style="green")
                table.add_column("Value")
                table.add_column("Description", style="dim")
                for entry in cfg["entries"]:
                    val = entry["value"] if entry["value"] is not None else "[dim]not set[/dim]"
                    table.add_row(entry["key"], val, entry.get("description", ""))
                console.print(table)


# Try to register pipe subcommands from the server at import time.
# If the server is not running, only the static commands (sync, list, add, remove) are available.
_register_pipe_commands()


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("sync")
def sync_all() -> None:
    """Sync all installed pipes."""
    try:
        for event in ShenasClient().sync_all():
            pipe = event.get("source", "")
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
        pipes = ShenasClient().plugins_list("source")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not pipes:
        console.print("[dim]No pipes installed[/dim]")
        return

    SIG_STYLE = {
        "valid": "[green]verified[/green]",
        "invalid": "[red]INVALID[/red]",
        "unsigned": "[yellow]unsigned[/yellow]",
        "no key": "[dim]no key[/dim]",
    }

    table = Table(show_lines=False)
    table.add_column("Source", style="green")
    table.add_column("Version", justify="right")
    table.add_column("Signature", justify="right")
    table.add_column("Commands")
    for p in pipes:
        cmds = ", ".join(p.get("commands", []))
        sig = SIG_STYLE.get(p.get("signature", ""), p.get("signature", ""))
        table.add_row(p["name"], p.get("version", ""), sig, cmds or "[dim]none[/dim]")
    console.print(table)


@app.command("schedule")
def schedule_cmd() -> None:
    """Show sync schedule for all pipes."""
    from rich.table import Table

    try:
        schedules = ShenasClient().get_sync_schedule()
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not schedules:
        console.print("[dim]No pipes have a sync schedule configured[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("Source", style="green")
    table.add_column("Frequency", justify="right")
    table.add_column("Last Sync")
    table.add_column("Due", justify="center")
    for s in schedules:
        freq = f"{s['sync_frequency']}m"
        synced = s["synced_at"] or "[dim]never[/dim]"
        due = "[green]yes[/green]" if s["is_due"] else "no"
        table.add_row(s["name"], freq, synced, due)
    console.print(table)


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Source names, e.g. 'garmin lunchmoney'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more pipe plugins from the repository."""
    for name in names:
        install(name, "source", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Source names, e.g. 'garmin lunchmoney'"),
) -> None:
    """Remove one or more pipe plugins."""
    for name in names:
        uninstall(name, "source")
