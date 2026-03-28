"""Parse YouTube data from Takeout exports (streaming with ijson)."""

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ijson


def parse_watch_history(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield YouTube watch history entries (streamed)."""
    for f in files:
        if f.name != "watch-history.json":
            continue

        with open(f, "rb") as fh:
            for entry in ijson.items(fh, "item"):
                yield {
                    "title": entry.get("title", ""),
                    "title_url": entry.get("titleUrl", ""),
                    "time": entry.get("time", ""),
                    "channel_name": (entry.get("subtitles", [{}])[0].get("name", "") if entry.get("subtitles") else ""),
                    "channel_url": (entry.get("subtitles", [{}])[0].get("url", "") if entry.get("subtitles") else ""),
                    "product": entry.get("header", ""),
                }


def parse_search_history(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield YouTube search history entries (streamed)."""
    for f in files:
        if f.name != "search-history.json":
            continue

        with open(f, "rb") as fh:
            for entry in ijson.items(fh, "item"):
                yield {
                    "title": entry.get("title", ""),
                    "title_url": entry.get("titleUrl", ""),
                    "time": entry.get("time", ""),
                    "product": entry.get("header", ""),
                }


def parse_subscriptions(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield YouTube subscriptions from CSV."""
    for f in files:
        if f.name != "subscriptions.csv":
            continue

        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        reader = csv.DictReader(text.splitlines())
        for row in reader:
            yield {
                "channel_id": row.get("Channel Id", row.get("channel_id", "")),
                "channel_url": row.get("Channel Url", row.get("channel_url", "")),
                "channel_title": row.get("Channel Title", row.get("channel_title", "")),
            }
