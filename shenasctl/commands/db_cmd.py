from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="Database commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command()
def keygen() -> None:
    """Generate a database encryption key and store it in the OS keyring."""
    try:
        ShenasClient().db_keygen()
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Database encryption key generated and stored in OS keyring.[/green]")


@app.command()
def status() -> None:
    """Show data summary per plugin."""
    try:
        data = ShenasClient().db_plugins()
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    table = Table(title="[bold]Data Summary[/bold]", show_lines=True)
    table.add_column("Plugin", style="green")
    table.add_column("Kind", style="dim")
    table.add_column("Rows", justify="right")
    table.add_column("Tables", justify="right")

    total_rows = 0
    for plugin in data:
        rows = plugin.get("totalRows", 0)
        tables = len(plugin.get("tables", []))
        if rows > 0 or tables > 0:
            table.add_row(
                plugin.get("displayName") or plugin["name"],
                plugin.get("kind", ""),
                str(rows),
                str(tables),
            )
            total_rows += rows

    if total_rows == 0:
        console.print("[dim]No data synced yet.[/dim]")
        return

    console.print(table)
    console.print(f"\n[bold]Total rows:[/bold] {total_rows:,}")
