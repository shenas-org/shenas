from __future__ import annotations

from typing import Any  # noqa: F401

import typer
from rich.console import Console
from rich.table import Table

from app.cli.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="Configuration management.", invoke_without_command=True)


def _client() -> ShenasClient:
    return ShenasClient()


def _handle_error(exc: ShenasServerError) -> None:
    console.print(f"[red]{exc.detail}[/red]")
    raise typer.Exit(code=1)


def _display_configs(configs: list[dict[str, Any]]) -> None:
    for cfg in configs:
        display_name = f"{cfg['kind']} {cfg['name']}"
        table = Table(title=f"[bold]{display_name}[/bold]", show_lines=False)
        table.add_column("Key", style="green")
        table.add_column("Value")
        table.add_column("Description", style="dim")

        for entry in cfg["entries"]:
            val = entry["value"] if entry["value"] is not None else "[dim]not set[/dim]"
            table.add_row(entry["key"], val, entry.get("description", ""))

        console.print(table)
        console.print()


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        try:
            configs = _client().config_list()
        except ShenasServerError as exc:
            _handle_error(exc)
        _display_configs(configs)
        raise typer.Exit()


@app.command("list")
def list_cmd(
    kind: str = typer.Argument(None, help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(None, help="Package name (e.g. 'garmin')"),
) -> None:
    """List config entries. Secrets are masked."""
    try:
        configs = _client().config_list(kind=kind, name=name)
    except ShenasServerError as exc:
        _handle_error(exc)
    _display_configs(configs)


@app.command("set")
def set_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name (e.g. 'lunchmoney')"),
    key: str = typer.Argument(help="Config key (e.g. 'api_key')"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a config value."""
    try:
        _client().config_set(kind, name, key, value)
    except ShenasServerError as exc:
        _handle_error(exc)
    console.print(f"[green]Set {kind} {name}.{key}[/green]")


@app.command("get")
def get_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name"),
    key: str = typer.Argument(help="Config key"),
) -> None:
    """Get a config value."""
    try:
        result = _client().config_get(kind, name, key)
    except ShenasServerError as exc:
        if exc.status_code == 404:
            console.print(f"[dim]Not set: {kind} {name}.{key}[/dim]")
            raise typer.Exit(code=1)
        _handle_error(exc)
    console.print(result["value"])


@app.command("delete")
def delete_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name"),
    key: str = typer.Argument(None, help="Config key (omit to delete all)"),
) -> None:
    """Delete a config entry or all config for a package."""
    try:
        _client().config_delete(kind, name, key)
    except ShenasServerError as exc:
        _handle_error(exc)

    if key:
        console.print(f"[green]Cleared {kind} {name}.{key}[/green]")
    else:
        console.print(f"[green]Deleted all config for {kind} {name}[/green]")
