import logging
from pathlib import Path

import dlt
import typer
from rich.console import Console

logging.getLogger("garth").setLevel(logging.CRITICAL)
logging.getLogger("garminconnect").setLevel(logging.CRITICAL)

console = Console()

app = typer.Typer(help="Garmin Connect commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

TOKEN_STORE = Path(".dlt") / "garmin_tokens"
DB_PATH = Path("data") / "local.duckdb"

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


@app.command()
def auth() -> None:
    """Authenticate with Garmin Connect and save the session token to disk.

    If Garmin is rate-limiting (429), run: uvx garth login
    That saves tokens to ~/.garth which you can copy to .dlt/garmin_tokens/.
    """
    from garminconnect import Garmin

    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)

    console.print("Authenticating...", style="dim")
    try:
        client = Garmin(email=email, password=password, return_on_mfa=True)
        client.garth.sess.headers.update({"User-Agent": BROWSER_UA})
        client.garth.oauth1_token = None
        client.garth.oauth2_token = None

        result1, result2 = client.login()

        if result1 == "needs_mfa":
            mfa_code = typer.prompt("MFA code")
            client.resume_login(result2, mfa_code)

    except Exception as exc:
        msg = str(exc)
        if "429" in msg:
            console.print("[red]Rate limited by Garmin.[/red] Try again later, use a different network, or run: uvx garth login")
        else:
            console.print(f"[red]Authentication failed:[/red] {msg}")
        raise typer.Exit(code=1)

    TOKEN_STORE.mkdir(parents=True, exist_ok=True)
    client.garth.dump(str(TOKEN_STORE))
    console.print(f"[green]Token saved to {TOKEN_STORE}[/green]")


@app.command()
def sync(
    start_date: str = typer.Option("30 days ago", help="Initial fetch window if no prior sync. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Garmin Connect data into DuckDB. Only fetches data not already loaded."""
    from shenas_pipes.garmin.auth import build_client
    from shenas_pipes.garmin.source import activities, body_composition, daily_stats, hrv, sleep, spo2
    from shenas_pipes.garmin.utils import resolve_start_date

    try:
        client = build_client(token_store=str(TOKEN_STORE))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    resolved = resolve_start_date(start_date)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    pipeline = dlt.pipeline(
        pipeline_name="garmin",
        destination=dlt.destinations.duckdb(credentials=str(DB_PATH)),
        dataset_name="garmin",
    )

    console.print(f"Syncing Garmin data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        activities(client, resolved),
        daily_stats(client, resolved),
        sleep(client, resolved),
        hrv(client, resolved),
        spo2(client, resolved),
        body_composition(client, resolved),
    ]

    load_info = pipeline.run(resources, refresh="drop_sources" if full_refresh else None)

    for package in load_info.load_packages:
        for job in package.jobs.get("completed_jobs", []):
            console.print(f"  [green]{job.job_file_info.table_name}[/green] — {job.job_file_info.job_id()}")


@app.command()
def transform() -> None:
    """Transform raw Garmin data into canonical metrics tables."""
    import duckdb

    from schema.ddl import ensure_schema
    from shenas_pipes.garmin.transform import GarminMetricProvider

    if not DB_PATH.exists():
        console.print(f"[red]Database not found at {DB_PATH}. Run sync first.[/red]")
        raise typer.Exit(code=1)

    con = duckdb.connect(str(DB_PATH))
    ensure_schema(con)

    provider = GarminMetricProvider()
    console.print("Transforming garmin...", style="dim")
    provider.transform(con)
    console.print("[green]done[/green]")
    con.close()
