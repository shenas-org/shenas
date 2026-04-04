from __future__ import annotations

import typer

from shenasctl.commands.plugin_cmd import DEFAULT_INDEX, install, register_plugin_commands, uninstall

app = typer.Typer(help="Schema commands.", invoke_without_command=True)

register_plugin_commands(app, "schema", "Installed Schemas")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("list")
def list_cmd() -> None:
    """List installed schema plugins."""
    from shenasctl.commands.plugin_cmd import list_plugins

    list_plugins("schema")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Schema names, e.g. 'fitness finance'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more schema plugins from the repository."""
    for name in names:
        install(name, "schema", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Schema names, e.g. 'fitness finance'"),
) -> None:
    """Remove one or more schema plugins."""
    for name in names:
        uninstall(name, "schema")


@app.command("flush")
def flush_cmd(
    names: list[str] = typer.Argument(help="Schema names, e.g. 'events fitness'"),
) -> None:
    """Delete all rows from a schema's metrics tables."""
    from rich.console import Console

    from shenasctl.client import api_request

    console = Console()
    for name in names:
        resp = api_request("DELETE", f"/db/schema/{name}/flush")
        if resp.get("rows_deleted") is not None:
            tables = ", ".join(resp["tables"])
            console.print(f"[green]Flushed {resp['rows_deleted']} rows from {name} ({tables})[/green]")
        else:
            console.print(f"[red]Failed to flush {name}: {resp.get('detail', 'unknown error')}[/red]")
