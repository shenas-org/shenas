import typer
from rich.console import Console
from rich.table import Table

from cli.client import ShenasClient, ShenasServerError
from cli.db import generate_db_key, set_db_key

console = Console()

app = typer.Typer(help="Database commands.", invoke_without_command=True)


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
    """Show database key source, file status, and table summary."""
    try:
        data = ShenasClient().db_status()
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    # Key source
    key_labels = {
        "env": "Key source: [green]SHENAS_DB_KEY environment variable[/green]",
        "keyring": "Key source: [green]OS keyring[/green]",
        "not_set": "Key source: [red]not set[/red]",
        "unavailable": "Key source: [red]keyring unavailable[/red]",
    }
    console.print(key_labels.get(data["key_source"], f"Key source: {data['key_source']}"))
    if data["key_source"] == "not_set":
        console.print("Run [bold]shenas db keygen[/bold] or set SHENAS_DB_KEY.")

    # DB file
    if data["size_mb"] is not None:
        console.print(f"Database: [green]{data['db_path']}[/green] ({data['size_mb']:.1f} MB)")
    else:
        console.print(f"Database: [dim]{data['db_path']} (not created yet)[/dim]")
        return

    # Table summary
    for schema_info in data.get("schemas", []):
        schema_name = schema_info["name"]
        label = "metrics  ·  canonical" if schema_name == "metrics" else f"metrics  ·  {schema_name}"
        table = Table(title=f"[bold]{label}[/bold]", show_lines=True)
        table.add_column("Table", style="green")
        table.add_column("Rows", justify="right")
        table.add_column("Earliest", justify="right")
        table.add_column("Latest", justify="right")
        table.add_column("Cols", justify="right")

        for t in schema_info["tables"]:
            table.add_row(
                t["name"],
                str(t["rows"]),
                t["earliest"] or "---",
                t["latest"] or "---",
                str(t["cols"]),
            )
        console.print(table)
