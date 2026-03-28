"""Google Takeout dlt resources -- parses extracted Takeout archives."""

from pathlib import Path
from typing import Any

import dlt

from shenas_pipes.gtakeout.drive import iter_files
from shenas_pipes.gtakeout.parsers.location import parse_location_records, parse_semantic_locations
from shenas_pipes.gtakeout.parsers.photos import parse_photos_metadata
from shenas_pipes.gtakeout.parsers.youtube import parse_search_history, parse_subscriptions, parse_watch_history


@dlt.resource(write_disposition="merge", primary_key="title")
def photos_metadata(extract_dir: Path) -> Any:
    """Yield photo/video metadata from Google Photos Takeout."""
    files = iter_files(extract_dir, "Google Photos")
    yield from parse_photos_metadata(files)


@dlt.resource(write_disposition="append")
def location_records(extract_dir: Path) -> Any:
    """Yield raw location records from Location History."""
    files = iter_files(extract_dir, "Location History (Timeline)")
    if not files:
        files = iter_files(extract_dir, "Location History")
    yield from parse_location_records(files)


@dlt.resource(write_disposition="append")
def location_visits(extract_dir: Path) -> Any:
    """Yield semantic location visits/activities."""
    files = iter_files(extract_dir, "Location History (Timeline)/Semantic Location History")
    if not files:
        files = iter_files(extract_dir, "Location History/Semantic Location History")
    yield from parse_semantic_locations(files)


@dlt.resource(write_disposition="append")
def youtube_watch_history(extract_dir: Path) -> Any:
    """Yield YouTube watch history."""
    files = iter_files(extract_dir, "YouTube and YouTube Music/history")
    yield from parse_watch_history(files)


@dlt.resource(write_disposition="append")
def youtube_search_history(extract_dir: Path) -> Any:
    """Yield YouTube search history."""
    files = iter_files(extract_dir, "YouTube and YouTube Music/history")
    yield from parse_search_history(files)


@dlt.resource(write_disposition="replace")
def youtube_subscriptions(extract_dir: Path) -> Any:
    """Yield YouTube subscriptions."""
    files = iter_files(extract_dir, "YouTube and YouTube Music/subscriptions", suffix=".csv")
    yield from parse_subscriptions(files)
