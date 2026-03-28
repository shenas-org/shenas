import os

import duckdb
import typer
from rich.console import Console
from rich.table import Table

from cli.db import DB_PATH, connect, generate_db_key, set_db_key

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

    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        console.print(f"Database: [green]{DB_PATH}[/green] ({size_mb:.1f} MB)")
    else:
        console.print(f"Database: [dim]{DB_PATH} (not created yet)[/dim]")
        return

    # Show table summary
    try:
        con = connect(read_only=True)
        schemas = _discover_schemas(con)
        for schema_name, tables in schemas.items():
            label = "metrics  ·  canonical" if schema_name == "metrics" else f"metrics  ·  {schema_name}"
            table = _make_table(label)
            for name in tables:
                if not name.startswith("_dlt_"):
                    _add_row(con, table, schema_name, name)
            console.print(table)
        con.close()
    except Exception:
        pass


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


def _make_table(title: str) -> Table:
    t = Table(title=f"[bold]{title}[/bold]", show_lines=True)
    t.add_column("Table", style="green")
    t.add_column("Rows", justify="right")
    t.add_column("Earliest", justify="right")
    t.add_column("Latest", justify="right")
    t.add_column("Cols", justify="right")
    return t


def _add_row(con: duckdb.DuckDBPyConnection, t: Table, schema: str, name: str) -> None:
    qualified = f"{schema}.{name}"
    row = con.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
    rows = row[0] if row else 0
    cols = len(con.execute(f"DESCRIBE {qualified}").fetchall())
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
