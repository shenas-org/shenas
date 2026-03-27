import logging
from pathlib import Path

import dlt
import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

logging.getLogger("garth").setLevel(logging.CRITICAL)
logging.getLogger("garminconnect").setLevel(logging.CRITICAL)

app = create_pipe_app("Garmin Connect commands.")

TOKEN_STORE = Path(".dlt") / "garmin_tokens"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


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
            console.print(
                "[red]Rate limited by Garmin.[/red] Try again later, use a different network, or run: uvx garth login"
            )
        else:
            console.print(f"[red]Authentication failed:[/red] {msg}")
        raise typer.Exit(code=1)

    TOKEN_STORE.mkdir(parents=True, exist_ok=True)
    client.garth.dump(str(TOKEN_STORE))
    console.print(f"[green]Token saved to {TOKEN_STORE}[/green]")


@app.command()
def sync(
    start_date: str = typer.Option(
        "30 days ago", help="Initial fetch window if no prior sync. Use 'YYYY-MM-DD' or 'N days ago'."
    ),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Garmin Connect data into DuckDB. Only fetches data not already loaded."""
    from shenas_pipes.core.utils import resolve_start_date
    from shenas_pipes.garmin.auth import build_client
    from shenas_pipes.garmin.source import activities, body_composition, daily_stats, hrv, sleep, spo2

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

    run_sync(pipeline, resources, full_refresh, _run_transform)


def _run_transform() -> None:
    from shenas_pipes.garmin.transform import GarminMetricProvider
    from shenas_schemas.fitness_tracker import ensure_schema

    con = connect()
    ensure_schema(con)

    provider = GarminMetricProvider()
    console.print("Transforming garmin...", style="dim")
    provider.transform(con)
    console.print("[green]done[/green]")
    con.close()


@app.command()
def transform() -> None:
    """Transform raw Garmin data into canonical metrics tables."""
    if not DB_PATH.exists():
        console.print(f"[red]Database not found at {DB_PATH}. Run sync first.[/red]")
        raise typer.Exit(code=1)
    _run_transform()
