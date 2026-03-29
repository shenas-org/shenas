from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

app = create_pipe_app("Strava commands.")


@app.command()
def sync(
    start_date: str = typer.Option("90 days ago", help="Initial fetch window. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Strava data into DuckDB and transform into canonical metrics."""
    from shenas_pipes.core.utils import resolve_start_date
    from shenas_pipes.strava.auth import build_client
    from shenas_pipes.strava.source import activities, athlete, athlete_stats

    client = build_client()
    resolved = resolve_start_date(start_date)

    console.print(f"Syncing Strava data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        activities(client, resolved),
        athlete(client),
        athlete_stats(client),
    ]

    def _transform() -> None:
        from shenas_pipes.strava.transform import StravaMetricProvider
        from shenas_schemas.fitness import ensure_schema

        con = connect()
        ensure_schema(con)
        provider = StravaMetricProvider()
        console.print("Transforming strava...", style="dim")
        provider.transform(con)
        console.print("[green]done[/green]")

    run_sync("strava", "strava", resources, full_refresh, _transform)
