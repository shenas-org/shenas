from __future__ import annotations

import typer

from shenasctl.commands.plugin_cmd import DEFAULT_INDEX, install, register_plugin_commands, uninstall

app = typer.Typer(help="Component commands.", invoke_without_command=True)

register_plugin_commands(app, "component", "Installed Components")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("list")
def list_cmd() -> None:
    """List installed component plugins."""
    from shenasctl.commands.plugin_cmd import list_plugins

    list_plugins("component")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Component names, e.g. 'fitness-dashboard'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more component plugins from the repository."""
    for name in names:
        install(name, "component", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Component names, e.g. 'fitness-dashboard'"),
) -> None:
    """Remove one or more component plugins."""
    for name in names:
        uninstall(name, "component")
