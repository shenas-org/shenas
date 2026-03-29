from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Spotify commands.")


@app.command()
def sync(
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
    time_range: str = typer.Option(
        "medium_term", help="Time range for top tracks/artists: short_term, medium_term, long_term."
    ),
) -> None:
    """Sync Spotify listening data into DuckDB.

    Recently played is limited to the last 50 tracks per sync.
    Run frequently (~1-2 hours) to build a complete listening history.
    """
    from shenas_pipes.spotify.auth import build_client
    from shenas_pipes.spotify.source import recently_played, saved_tracks, top_artists, top_tracks

    client = build_client()

    console.print(f"Syncing Spotify data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        recently_played(client),
        top_tracks(client, time_range=time_range),
        top_artists(client, time_range=time_range),
        saved_tracks(client),
    ]

    run_sync("spotify", "spotify", resources, full_refresh)
