from __future__ import annotations

import typer

from shenasctl.commands.plugin_cmd import DEFAULT_INDEX, install, register_plugin_commands, uninstall

app = typer.Typer(help="Theme commands.", invoke_without_command=True)

register_plugin_commands(app, "theme", "Installed Themes")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_cmd() -> None:
    """List installed theme plugins."""
    from shenasctl.commands.plugin_cmd import list_plugins

    list_plugins("theme")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Theme plugin names"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more theme plugins from the repository."""
    for name in names:
        install(name, "theme", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Theme plugin names"),
) -> None:
    """Remove one or more theme plugins."""
    for name in names:
        uninstall(name, "theme")
