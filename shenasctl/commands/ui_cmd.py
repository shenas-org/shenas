from __future__ import annotations

import typer

from shenasctl.commands.plugin_cmd import DEFAULT_INDEX, install, register_plugin_commands, uninstall

app = typer.Typer(help="UI commands.", invoke_without_command=True)

register_plugin_commands(app, "ui", "Installed UI")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("list")
def list_cmd() -> None:
    """List installed UI plugins."""
    from shenasctl.commands.plugin_cmd import list_plugins

    list_plugins("ui")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="UI plugin names"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more UI plugins from the repository."""
    for name in names:
        install(name, "ui", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="UI plugin names"),
) -> None:
    """Remove one or more UI plugins."""
    for name in names:
        uninstall(name, "ui")
