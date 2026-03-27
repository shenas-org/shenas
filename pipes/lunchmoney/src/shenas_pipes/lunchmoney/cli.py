from pathlib import Path

import dlt
import typer
from rich.console import Console

console = Console()

app = typer.Typer(help="Lunch Money commands.", invoke_without_command=True)

TOKEN_STORE = Path(".dlt") / "lunchmoney_token"
DB_PATH = Path("data") / "local.duckdb"


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


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
        user = client.get_me()
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
    from shenas_pipes.lunchmoney.utils import resolve_start_date

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

    load_info = pipeline.run(resources, refresh="drop_sources" if full_refresh else None)

    for package in load_info.load_packages:
        for job in package.jobs.get("completed_jobs", []):
            console.print(f"  [green]{job.job_file_info.table_name}[/green] -- {job.job_file_info.job_id()}")
