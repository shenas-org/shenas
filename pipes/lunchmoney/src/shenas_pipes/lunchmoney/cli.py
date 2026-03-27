from pathlib import Path

import dlt
import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

app = create_pipe_app("Lunch Money commands.")

TOKEN_STORE = Path(".dlt") / "lunchmoney_token"


@app.command()
def auth() -> None:
    """Store a Lunch Money API key.

    Get your key from: Lunch Money > Settings > Developers > Request new Access Token
    """
    from shenas_pipes.lunchmoney.auth import build_client

    api_key = typer.prompt("API key", hide_input=True)

    console.print("Verifying...", style="dim")
    try:
        client = build_client(api_key=api_key, token_store=str(TOKEN_STORE))
        user = client.get_user()
        console.print(f"[green]Authenticated as {user.user_name} ({user.user_email})[/green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    start_date: str = typer.Option("90 days ago", help="Initial fetch window. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Lunch Money data into DuckDB. Only fetches new transactions on subsequent runs."""
    from shenas_pipes.core.utils import resolve_start_date
    from shenas_pipes.lunchmoney.auth import build_client
    from shenas_pipes.lunchmoney.source import (
        assets,
        budgets,
        categories,
        plaid_accounts,
        recurring_items,
        tags,
        transactions,
    )

    try:
        client = build_client(token_store=str(TOKEN_STORE))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    resolved = resolve_start_date(start_date)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    pipeline = dlt.pipeline(
        pipeline_name="lunchmoney",
        destination=dlt.destinations.duckdb(credentials=str(DB_PATH)),
        dataset_name="lunchmoney",
    )

    console.print(f"Syncing Lunch Money data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        transactions(client, resolved),
        categories(client),
        tags(client),
        budgets(client, resolved),
        recurring_items(client),
        assets(client),
        plaid_accounts(client),
    ]

    run_sync(pipeline, resources, full_refresh, _run_transform)


def _run_transform() -> None:
    from shenas_pipes.lunchmoney.transform import LunchMoneyMetricProvider
    from shenas_schemas.finance import ensure_schema

    con = connect()
    ensure_schema(con)

    provider = LunchMoneyMetricProvider()
    console.print("Transforming lunchmoney...", style="dim")
    provider.transform(con)
    console.print("[green]done[/green]")
    con.close()


@app.command()
def transform() -> None:
    """Transform raw Lunch Money data into canonical metrics tables."""
    if not DB_PATH.exists():
        console.print(f"[red]Database not found at {DB_PATH}. Run sync first.[/red]")
        raise typer.Exit(code=1)
    _run_transform()
