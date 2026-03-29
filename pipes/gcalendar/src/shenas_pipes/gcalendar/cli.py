from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Google Calendar commands.")

DISPLAY_NAME = "Google Calendar"
DESCRIPTION = """Syncs events and calendar metadata from Google Calendar.

Uses Google OAuth2 with shared credentials from shenas-pipe-core.

Resources: events (incremental), calendars.
No transform step -- raw data stored in gcalendar.* schema."""


@app.command()
def sync(
    start_date: str = typer.Option("30 days ago", help="Fetch events from this date. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
) -> None:
    """Sync Google Calendar events from all calendars into DuckDB."""
    from shenas_pipes.gcalendar.auth import build_client
    from shenas_pipes.gcalendar.source import calendars, events

    service = build_client()
    console.print(f"Syncing Google Calendar data into [bold]{DB_PATH}[/bold]...", style="dim")

    # Fetch events from all calendars, not just primary
    cal_list = service.calendarList().list().execute().get("items", [])
    event_resources = [events(service, start_date=start_date, calendar_id=cal["id"]) for cal in cal_list]

    resources = [*event_resources, calendars(service)]

    run_sync("gcalendar", "gcalendar", resources, full_refresh)
