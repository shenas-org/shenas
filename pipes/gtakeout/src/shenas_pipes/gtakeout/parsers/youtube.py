"""Parse YouTube data from Takeout exports."""

import csv
import json
from pathlib import Path
from typing import Any


def parse_watch_history(files: list[Path]) -> list[dict[str, Any]]:
    """Parse YouTube watch history from watch-history.json."""
    items = []
    for f in files:
        if f.name != "watch-history.json":
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for entry in data:
            items.append(
                {
                    "title": entry.get("title", ""),
                    "title_url": entry.get("titleUrl", ""),
                    "time": entry.get("time", ""),
                    "channel_name": (entry.get("subtitles", [{}])[0].get("name", "") if entry.get("subtitles") else ""),
                    "channel_url": (entry.get("subtitles", [{}])[0].get("url", "") if entry.get("subtitles") else ""),
                    "product": entry.get("header", ""),
                }
            )

    return items


def parse_search_history(files: list[Path]) -> list[dict[str, Any]]:
    """Parse YouTube search history from search-history.json."""
    items = []
    for f in files:
        if f.name != "search-history.json":
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for entry in data:
            items.append(
                {
                    "title": entry.get("title", ""),
                    "title_url": entry.get("titleUrl", ""),
                    "time": entry.get("time", ""),
                    "product": entry.get("header", ""),
                }
            )

    return items


def parse_subscriptions(files: list[Path]) -> list[dict[str, Any]]:
    """Parse YouTube subscriptions from subscriptions.csv."""
    items = []
    for f in files:
        if f.name != "subscriptions.csv":
            continue

        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        reader = csv.DictReader(text.splitlines())
        for row in reader:
            items.append(
                {
                    "channel_id": row.get("Channel Id", row.get("channel_id", "")),
                    "channel_url": row.get("Channel Url", row.get("channel_url", "")),
                    "channel_title": row.get("Channel Title", row.get("channel_title", "")),
                }
            )

    return items
