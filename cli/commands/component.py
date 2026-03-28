from pathlib import Path

import typer

from cli.commands.pkg import DEFAULT_INDEX, install, list_packages, uninstall

app = typer.Typer(help="Component commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_cmd() -> None:
    """List installed component packages."""
    list_packages("component")


@app.command("add")
def add_cmd(
    name: str = typer.Argument(help="Component name, e.g. 'fitness-dashboard'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    public_key: Path = typer.Option(Path(".shenas/shenas.pub"), "--public-key", help="Path to Ed25519 public key"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add a component package from the repository."""
    install(name, "component", index_url, public_key, skip_verify)


@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(help="Component name, e.g. 'fitness-dashboard'"),
) -> None:
    """Remove a component package."""
    uninstall(name, "component")
