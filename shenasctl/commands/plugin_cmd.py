"""Shared install/uninstall/list/describe logic for all plugin types.

The data-returning functions (list_plugins_data, install_plugin, uninstall_plugin)
are called by both the REST API and the CLI display helpers below.
"""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

DEFAULT_INDEX = "http://127.0.0.1:7290"

SIG_STYLE = {
    "valid": "[green]verified[/green]",
    "invalid": "[red]INVALID[/red]",
    "unsigned": "[yellow]unsigned[/yellow]",
    "no key": "[dim]no key[/dim]",
}


# --- CLI display functions (call server) ---


def list_plugins(kind: str) -> None:
    """List plugins via the REST API and display as a rich table."""
    try:
        items = ShenasClient().plugins_list(kind)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not items:
        console.print(f"[dim]No {kind} plugins installed[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column(kind.capitalize(), style="green")
    table.add_column("Package")
    table.add_column("Version", justify="right")
    table.add_column("Signature", justify="right")
    for p in items:
        table.add_row(p["name"], p["package"], p["version"], SIG_STYLE.get(p["signature"], p["signature"]))
    console.print(table)


def install(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    skip_verify: bool = False,
) -> None:
    """Install a plugin via the REST API."""
    try:
        result = ShenasClient().plugins_add(kind, [name], index_url=index_url, skip_verify=skip_verify)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    for r in result.get("results", []):
        if r["ok"]:
            console.print(f"[green]{r['message']}[/green]")
        else:
            console.print(f"[red]{r['message']}[/red]")
            raise typer.Exit(code=1)


def uninstall(name: str, kind: str) -> None:
    """Uninstall a plugin via the REST API."""
    try:
        result = ShenasClient().plugins_remove(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if result["ok"]:
        console.print(f"[green]{result['message']}[/green]")
    else:
        console.print(f"[red]{result['message']}[/red]")
        raise typer.Exit(code=1)


def info(name: str, kind: str) -> None:
    """Show full info for an installed plugin."""
    try:
        result = ShenasClient().plugins_info(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    display = result.get("display_name") or name
    console.print(f"\n[bold]{display}[/bold] ({kind}: {name})\n")

    desc = result.get("description", "")
    if desc:
        console.print(desc)
        console.print()

    from rich.table import Table

    table = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    enabled = result.get("enabled", True)
    table.add_row("Status", "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]")
    if result.get("added_at"):
        table.add_row("Added", result["added_at"][:19])
    if result.get("updated_at"):
        table.add_row("Updated", result["updated_at"][:19])
    if result.get("status_changed_at"):
        table.add_row("Status changed", result["status_changed_at"][:19])
    if result.get("synced_at"):
        table.add_row("Last synced", result["synced_at"][:19])

    console.print(table)
    console.print()


def enable(name: str, kind: str) -> None:
    """Enable a plugin."""
    try:
        result = ShenasClient().plugins_enable(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]{result.get('message', 'Enabled')}[/green]")


def disable(name: str, kind: str) -> None:
    """Disable a plugin."""
    try:
        result = ShenasClient().plugins_disable(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]{result.get('message', 'Disabled')}[/yellow]")


def register_plugin_commands(parent_app: typer.Typer, kind: str, panel: str) -> list[dict[str, Any]]:
    """Discover installed plugins from the server and register subcommands.

    Registers commands based on what the server reports for each plugin.
    Returns the list of plugin info dicts for further processing by
    plugin-specific CLIs (e.g. pipes add sync/auth/config).
    """
    try:
        plugins = ShenasClient().plugins_list(kind)
    except Exception:
        return []

    for plugin in plugins:
        name = plugin["name"]
        commands = plugin.get("commands", [])
        plugin_app = typer.Typer(help=f"{name} {kind}.", invoke_without_command=True)

        @plugin_app.callback()
        def _default(ctx: typer.Context) -> None:
            if ctx.invoked_subcommand is None:
                typer.echo(ctx.get_help())
                raise typer.Exit

        if "describe" in commands:
            _add_info(plugin_app, name, kind)

        parent_app.add_typer(plugin_app, name=name, rich_help_panel=panel)

    return plugins


def _add_info(plugin_app: typer.Typer, plugin_name: str, plugin_kind: str) -> None:
    @plugin_app.command("info")
    def _info() -> None:
        """Show info about this plugin."""
        info(plugin_name, plugin_kind)
