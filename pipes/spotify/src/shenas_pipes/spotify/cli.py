from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Spotify commands.")

PIPE_DESCRIPTION = """Syncs listening data from Spotify.

Uses OAuth2 PKCE flow (no client secret needed). Create an app at
developer.spotify.com/dashboard with redirect URI http://127.0.0.1:8090/callback.

Resources: recently_played (incremental, last 50 tracks per sync),
top_tracks, top_artists (by time range), saved_tracks.
Import: shenasctl pipe spotify import /path/to/export/ for historical data.
Poll frequently (~1-2 hours) to build complete listening history."""


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


@app.command("import")
def import_history(
    export_dir: str = typer.Argument(help="Path to extracted Spotify export directory."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop existing history and re-import."),
) -> None:
    """Import streaming history from a Spotify data export.

    Request your data at: https://www.spotify.com/account/privacy/

    Point this command at the extracted directory containing the JSON files
    (endsong_*.json, Streaming_History_Audio_*.json, or StreamingHistory*.json).
    """
    from pathlib import Path

    from shenas_pipes.spotify.history_import import streaming_history

    path = Path(export_dir).expanduser()
    if not path.is_dir():
        console.print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Importing Spotify history from [bold]{path}[/bold] into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [streaming_history(path)]
    run_sync("spotify", "spotify", resources, full_refresh)
