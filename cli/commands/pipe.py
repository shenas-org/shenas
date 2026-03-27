from importlib.metadata import entry_points
from pathlib import Path

import typer

from cli.commands.pkg import DEFAULT_INDEX, install, list_packages, uninstall

app = typer.Typer(help="Pipeline commands.", invoke_without_command=True)

for _ep in entry_points(group="shenas.pipes"):
    app.add_typer(_ep.load(), name=_ep.name)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_cmd() -> None:
    """List installed pipe packages."""
    list_packages("pipe")


@app.command("add")
def add_cmd(
    name: str = typer.Argument(help="Pipe name, e.g. 'garmin'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    public_key: Path = typer.Option(Path(".shenas/shenas.pub"), "--public-key", help="Path to Ed25519 public key"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Add a pipe package from the repository."""
    install(name, "pipe", index_url, public_key, skip_verify)


@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(help="Pipe name, e.g. 'garmin'"),
) -> None:
    """Remove a pipe package."""
    uninstall(name, "pipe")
