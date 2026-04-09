"""Goodreads RSS feed client.

Goodreads exposes public shelf data via RSS at
``goodreads.com/review/list_rss/<user_id>?shelf=<shelf>&page=<n>``.
Each page returns up to 100 items. We paginate until we get an empty
page.

The RSS items contain book metadata, user rating, dates, review text,
and shelf assignments -- enough to populate all three tables without
HTML scraping.
"""

from __future__ import annotations

from typing import Any

import feedparser
import httpx

BASE_URL = "https://www.goodreads.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Shelves to fetch by default
DEFAULT_SHELVES = ("read", "currently-reading", "to-read")


def _parse_int(val: str | None) -> int | None:
    if not val or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None


def _parse_float(val: str | None) -> float | None:
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def _parse_date(val: str | None) -> str | None:
    """Parse an RFC 2822 date (from RSS) into ISO date string."""
    if not val or not val.strip():
        return None
    import email.utils
    from datetime import UTC

    parsed = email.utils.parsedate_to_datetime(val)
    if parsed.year < 2000:
        return None
    return parsed.astimezone(UTC).strftime("%Y-%m-%d")


class GoodreadsClient:
    """Fetches public Goodreads shelf data via RSS feeds."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def _fetch_shelf_page(self, shelf: str, page: int) -> list[dict[str, Any]]:
        """Fetch one page of RSS items for a shelf."""
        url = f"{BASE_URL}/review/list_rss/{self._user_id}"
        resp = self._http.get(url, params={"shelf": shelf, "page": page})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        return feed.entries

    def get_shelf(self, shelf: str) -> list[dict[str, Any]]:
        """Fetch all items from a shelf, paginating until empty."""
        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            entries = self._fetch_shelf_page(shelf, page)
            if not entries:
                break
            all_items.extend(entries)
            page += 1
        return all_items

    def get_all_shelves(self, shelves: tuple[str, ...] = DEFAULT_SHELVES) -> list[dict[str, Any]]:
        """Fetch items from all specified shelves.

        Each item is annotated with a ``_shelf`` key indicating which
        shelf it came from. Deduplicates by book_id (a book on multiple
        custom shelves appears in each, but we keep the first with the
        most data).
        """
        seen: dict[str, dict[str, Any]] = {}
        for shelf in shelves:
            for entry in self.get_shelf(shelf):
                book_id = entry.get("book_id", "")
                if not book_id:
                    continue
                entry["_shelf"] = shelf
                if book_id not in seen:
                    seen[book_id] = entry
                else:
                    # Merge shelf info: keep the entry that has a user_read_at if available
                    existing = seen[book_id]
                    if not existing.get("user_read_at") and entry.get("user_read_at"):
                        entry["_shelves"] = existing.get("_shelves", existing.get("_shelf", ""))
                        seen[book_id] = entry
                    # Accumulate shelves
                    shelves_str = seen[book_id].get("_shelves", seen[book_id].get("_shelf", ""))
                    if shelf not in shelves_str:
                        seen[book_id]["_shelves"] = f"{shelves_str}, {shelf}" if shelves_str else shelf
        return list(seen.values())

    @staticmethod
    def parse_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """Normalize a feedparser entry into a flat dict."""
        # feedparser flattens RSS custom elements as attributes
        return {
            "book_id": entry.get("book_id", ""),
            "title": entry.get("title", "").strip() or None,
            "author": entry.get("author_name", "").strip() or None,
            "isbn": entry.get("isbn", "").strip() or None,
            "num_pages": _parse_int(entry.get("book", {}).get("num_pages") if isinstance(entry.get("book"), dict) else None),
            "year_published": _parse_int(entry.get("book_published")),
            "average_rating": _parse_float(entry.get("average_rating")),
            "my_rating": _parse_int(entry.get("user_rating")),
            "date_read": _parse_date(entry.get("user_read_at")),
            "date_added": _parse_date(entry.get("user_date_added")),
            "user_shelves": entry.get("user_shelves", "").strip() or None,
            "exclusive_shelf": entry.get("_shelf", ""),
            "my_review": entry.get("user_review", "").strip() or None,
        }
