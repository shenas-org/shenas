"""Parse Chrome data from Takeout exports (streaming with ijson)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import ijson

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def parse_browser_history(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield Chrome browser history entries (streamed)."""
    for path in files:
        if path.name != "History.json":
            continue

        with open(path, "rb") as fh:
            for entry in ijson.items(fh, "Browser History.item"):
                time_usec = entry.get("time_usec", 0)
                try:
                    timestamp = datetime.fromtimestamp(time_usec / 1_000_000, tz=UTC).isoformat()
                except (ValueError, OSError, OverflowError):
                    continue

                url = entry.get("url", "")
                if not url:
                    continue

                yield {
                    "url": url,
                    "title": entry.get("title", ""),
                    "timestamp": timestamp,
                    "favicon_url": entry.get("favicon_url", ""),
                    "page_transition": entry.get("page_transition", ""),
                    "client_id": entry.get("client_id", ""),
                }
