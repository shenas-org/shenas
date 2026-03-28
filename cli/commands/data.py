from pathlib import Path

import duckdb
import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(help="Data inspection and transformation commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


DB_PATH = Path("data") / "local.duckdb"


def _discover_schemas(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    """Discover all non-system schemas and their tables."""
    rows = con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema', 'main') "
        "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
        "ORDER BY table_schema, table_name"
    ).fetchall()
    schemas: dict[str, list[str]] = {}
    for schema, table in rows:
        schemas.setdefault(schema, []).append(table)
    return schemas


@app.command()
def status() -> None:
    """Show row counts and date ranges for all tables."""
    if not DB_PATH.exists():
        console.print(f"[red]Database not found at {DB_PATH}[/red]")
        raise typer.Exit(code=1)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    schemas = _discover_schemas(con)

    def make_table(title: str) -> Table:
        t = Table(title=f"[bold]{title}[/bold]", show_lines=True)
        t.add_column("Table", style="green")
        t.add_column("Rows", justify="right")
        t.add_column("Earliest", justify="right")
        t.add_column("Latest", justify="right")
        t.add_column("Cols", justify="right")
        return t

    def add_row(t: Table, schema: str, name: str) -> None:
        qualified = f"{schema}.{name}"
        row = con.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
        rows = row[0] if row else 0
        cols = len(con.execute(f"DESCRIBE {qualified}").fetchall())
        # Try common date column names
        for date_col in ("date", "calendar_date", "start_time_local"):
            try:
                res = con.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
                if res is None:
                    continue
                earliest = str(res[0])[:10] if res[0] else "—"
                latest = str(res[1])[:10] if res[1] else "—"
                t.add_row(name, str(rows), earliest, latest, str(cols))
                return
            except duckdb.Error:
                continue
        t.add_row(name, str(rows), "—", "—", str(cols))

    for schema_name, tables in schemas.items():
        label = "metrics  ·  canonical" if schema_name == "metrics" else f"metrics  ·  {schema_name}"
        table = make_table(label)
        for name in tables:
            if not name.startswith("_dlt_"):
                add_row(table, schema_name, name)
        console.print(table)

    con.close()
