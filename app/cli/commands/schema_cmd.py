from __future__ import annotations

import typer

from app.cli.commands.pkg import DEFAULT_INDEX, install, list_packages, uninstall

app = typer.Typer(help="Schema commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_cmd() -> None:
    """List installed schema packages."""
    list_packages("schema")


@app.command("add")
def add_cmd(
    names: list[str] = typer.Argument(help="Schema names, e.g. 'fitness finance'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add one or more schema packages from the repository."""
    for name in names:
        install(name, "schema", index_url, skip_verify)


@app.command("remove")
def remove_cmd(
    names: list[str] = typer.Argument(help="Schema names, e.g. 'fitness finance'"),
) -> None:
    """Remove one or more schema packages."""
    for name in names:
        uninstall(name, "schema")
