import shutil
import tempfile
from pathlib import Path

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH

app = create_pipe_app("Google Takeout commands.")


@app.command()
def sync(
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
    latest: int = typer.Option(0, "--latest", help="Only process the N most recent archives (0 = all)."),
) -> None:
    """Find Takeout archives on Google Drive, download, extract, and load into DuckDB."""
    from shenas_pipes.gtakeout.auth import build_client
    from shenas_pipes.gtakeout.drive import download_archive, extract_archive, find_takeout_archives
    from shenas_pipes.gtakeout.source import (
        location_records,
        location_visits,
        photos_metadata,
        youtube_search_history,
        youtube_subscriptions,
        youtube_watch_history,
    )

    service = build_client()

    archives = find_takeout_archives(service)
    if not archives:
        raise RuntimeError(
            "No Takeout archives found on Google Drive. Go to https://takeout.google.com and export to Google Drive first."
        )

    if latest > 0:
        archives = archives[:latest]

    total_size = sum(a["size"] for a in archives)
    total_mb = total_size / (1024 * 1024)

    # Check disk space
    tmp_root = Path(tempfile.gettempdir())
    free_mb = shutil.disk_usage(tmp_root).free / (1024 * 1024)
    # Need ~2x archive size (download + extraction)
    needed_mb = total_mb * 2
    if free_mb < needed_mb:
        raise RuntimeError(
            f"Insufficient disk space. Need ~{needed_mb:.0f} MB but only {free_mb:.0f} MB free in {tmp_root}. "
            f"Use --latest N to process fewer archives."
        )

    console.print(f"Processing {len(archives)} archive(s) ({total_mb:.0f} MB) into [bold]{DB_PATH}[/bold]", style="dim")

    tmp_dir = Path(tempfile.mkdtemp(prefix="takeout_"))
    try:
        for archive_info in archives:
            size_mb = archive_info["size"] / (1024 * 1024)
            console.print(f"Downloading {archive_info['name']} ({size_mb:.0f} MB)...", style="dim")
            archive_path = download_archive(service, archive_info["id"], tmp_dir)

            console.print(f"Extracting {archive_info['name']}...", style="dim")
            extract_dir = extract_archive(archive_path, tmp_dir)

            console.print("Loading data...", style="dim")
            resources = [
                photos_metadata(extract_dir),
                location_records(extract_dir),
                location_visits(extract_dir),
                youtube_watch_history(extract_dir),
                youtube_search_history(extract_dir),
                youtube_subscriptions(extract_dir),
            ]

            run_sync("gtakeout", "gtakeout", resources, full_refresh)

            # Clean up this archive's files (keep tmp_dir for next archive)
            shutil.rmtree(extract_dir, ignore_errors=True)
            archive_path.unlink(missing_ok=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
