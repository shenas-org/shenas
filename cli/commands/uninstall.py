import subprocess

import typer
from rich.console import Console

console = Console()

app = typer.Typer(help="Uninstall packages.", invoke_without_command=True)

PREFIXES = {"pipe": "shenas-pipe-", "schema": "shenas-schema-", "component": "shenas-component-"}


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def pipe(
    name: str = typer.Argument(help="Pipe name, e.g. 'garmin'"),
) -> None:
    """Uninstall a pipe package."""
    pkg_name = f"{PREFIXES['pipe']}{name}"

    result = subprocess.run(
        ["uv", "pip", "uninstall", pkg_name],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        console.print(f"[green]Uninstalled {pkg_name}[/green]")
        if result.stdout.strip():
            console.print(result.stdout.strip(), style="dim")
    else:
        console.print(f"[red]Failed to uninstall {pkg_name}[/red]")
        if result.stderr.strip():
            console.print(result.stderr.strip(), style="dim")
        raise typer.Exit(code=1)
