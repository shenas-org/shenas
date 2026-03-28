import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Google Photos commands.")


@app.command()
def sync(
    start_date: str = typer.Option("30 days ago", help="Fetch media from this date. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
) -> None:
    """Sync Google Photos media items and albums into DuckDB."""
    from shenas_pipes.gphotos.auth import build_client
    from shenas_pipes.gphotos.source import albums, media_items

    service = build_client()
    console.print(f"Syncing Google Photos data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        media_items(service, start_date=start_date),
        albums(service),
    ]

    run_sync("gphotos", "gphotos", resources, full_refresh)
