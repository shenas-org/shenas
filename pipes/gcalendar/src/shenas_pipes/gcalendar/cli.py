import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Google Calendar commands.")


@app.command()
def sync(
    start_date: str = typer.Option("30 days ago", help="Fetch events from this date. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
) -> None:
    """Sync Google Calendar events into DuckDB."""
    from shenas_pipes.gcalendar.auth import build_client
    from shenas_pipes.gcalendar.source import calendars, events

    try:
        service = build_client()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Syncing Google Calendar data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        events(service, start_date=start_date),
        calendars(service),
    ]

    run_sync("gcalendar", "gcalendar", resources, full_refresh)
