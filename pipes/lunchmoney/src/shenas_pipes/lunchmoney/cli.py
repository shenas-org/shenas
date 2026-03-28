import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

app = create_pipe_app("Lunch Money commands.")


@app.command()
def auth() -> None:
    """Store a Lunch Money API key in OS keyring.

    Get your key from: Lunch Money > Settings > Developers > Request new Access Token
    """
    from shenas_pipes.lunchmoney.auth import build_client

    api_key = typer.prompt("API key", hide_input=True)

    console.print("Verifying...", style="dim")
    try:
        client = build_client(api_key=api_key)
        user = client.get_user()
        console.print(f"[green]Authenticated as {user.user_name} ({user.user_email})[/green]")
        console.print("[green]API key saved to OS keyring[/green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    start_date: str = typer.Option("90 days ago", help="Initial fetch window. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Lunch Money data into DuckDB and transform into canonical metrics."""
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

    client = build_client()
    resolved = resolve_start_date(start_date)

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

    def _transform() -> None:
        from shenas_pipes.lunchmoney.transform import LunchMoneyMetricProvider
        from shenas_schemas.finance import ensure_schema

        con = connect()
        ensure_schema(con)
        provider = LunchMoneyMetricProvider()
        console.print("Transforming lunchmoney...", style="dim")
        provider.transform(con)
        console.print("[green]done[/green]")

    run_sync("lunchmoney", "lunchmoney", resources, full_refresh, _transform)
