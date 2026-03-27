from pathlib import Path

import duckdb
import typer
from rich.console import Console
from rich.table import Table

from schema.ddl import CANONICAL_TABLES

console = Console()

app = typer.Typer(help="Data inspection and transformation commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

DB_PATH = Path("data") / "local.duckdb"

GARMIN_TABLES = ["activities", "daily_stats", "sleep", "hrv", "spo2", "body_composition"]


@app.command()
def status() -> None:
    """Show row counts and date ranges for raw and canonical tables."""
    if not DB_PATH.exists():
        console.print(f"[red]Database not found at {DB_PATH}[/red]")
        raise typer.Exit(code=1)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    existing_garmin = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'garmin'"
        ).fetchall()
    }
    existing_metrics = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'"
        ).fetchall()
    }

    date_columns = {
        "activities": "start_time_local",
        "daily_stats": "calendar_date",
        "sleep": "calendar_date",
        "hrv": "calendar_date",
        "spo2": "calendar_date",
        "body_composition": "calendar_date",
    }

    def make_table(title: str) -> Table:
        t = Table(title=f"[bold]{title}[/bold]", show_lines=True)
        t.add_column("Table", style="green")
        t.add_column("Rows", justify="right")
        t.add_column("Earliest", justify="right")
        t.add_column("Latest", justify="right")
        t.add_column("Cols", justify="right")
        return t

    def add_row(t: Table, schema: str, name: str, date_col: str, exists: bool) -> None:
        if not exists:
            t.add_row(name, "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]")
            return
        qualified = f"{schema}.{name}"
        rows = con.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE {qualified}").fetchall())
        try:
            res = con.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
            earliest = str(res[0])[:10] if res[0] else "—"
            latest = str(res[1])[:10] if res[1] else "—"
        except duckdb.Error:
            earliest = latest = "—"
        t.add_row(name, str(rows), earliest, latest, str(cols))

    raw = make_table(f"metrics  ·  garmin")
    for name in GARMIN_TABLES:
        add_row(raw, "garmin", name, date_columns.get(name, "date"), name in existing_garmin)
    console.print(raw)

    canonical = make_table("metrics  ·  canonical")
    for name in CANONICAL_TABLES:
        add_row(canonical, "metrics", name, "date", name in existing_metrics)
    console.print(canonical)

    con.close()


