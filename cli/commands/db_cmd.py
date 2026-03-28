import os

import typer
from rich.console import Console

from cli.db import DB_PATH, generate_db_key, set_db_key

console = Console()

app = typer.Typer(help="Database management commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def keygen() -> None:
    """Generate a database encryption key and store it in the OS keyring."""
    key = generate_db_key()
    set_db_key(key)
    console.print("[green]Database encryption key generated and stored in OS keyring.[/green]")


@app.command()
def status() -> None:
    """Show database key and file status."""
    # Check env var
    if os.environ.get("SHENAS_DB_KEY"):
        console.print("Key source: [green]SHENAS_DB_KEY environment variable[/green]")
    else:
        try:
            import keyring

            key = keyring.get_password("shenas", "db_key")
            if key:
                console.print("Key source: [green]OS keyring[/green]")
            else:
                console.print("Key source: [red]not set[/red]")
                console.print("Run [bold]shenas db keygen[/bold] or set SHENAS_DB_KEY.")
        except Exception:
            console.print("Key source: [red]keyring unavailable[/red]")

    # Check DB file
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        console.print(f"Database: [green]{DB_PATH}[/green] ({size_mb:.1f} MB)")
    else:
        console.print(f"Database: [dim]{DB_PATH} (not created yet)[/dim]")
