"""Firefox source tables.

Reads from Firefox's local ``places.sqlite`` database. The ``client``
argument is the path to a temporary copy of that file.

- ``Visits`` is an ``EventTable`` joining ``moz_historyvisits`` +
  ``moz_places``. Firefox does not store visit duration, so there is no
  interval end.
- ``Bookmarks`` is a ``DimensionTable`` loaded as SCD2 to track when
  bookmarks are added or removed.

Firefox timestamps are microseconds since Unix epoch (unlike Chrome's
1601-based epoch).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import DimensionTable, EventTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _firefox_time(us: int | None) -> str | None:
    """Convert Firefox timestamp (microseconds since Unix epoch) to ISO 8601."""
    if not us or us <= 0:
        return None
    try:
        return datetime.fromtimestamp(us / 1_000_000, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


_VISIT_TYPE: dict[int, str] = {
    1: "link",
    2: "typed",
    3: "bookmark",
    4: "embed",
    5: "redirect_permanent",
    6: "redirect_temporary",
    7: "download",
    8: "framed_link",
    9: "reload",
}


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Visits(EventTable):
    """Individual page visit from Firefox browsing history."""

    class _Meta:
        name = "visits"
        display_name = "Visits"
        description = "Individual page visits from Firefox browsing history."
        pk = ("id",)

    time_at: ClassVar[str] = "visit_time"
    cursor_column: ClassVar[str] = "visit_time"

    id: Annotated[int, Field(db_type="BIGINT", description="Firefox visit ID")] = 0
    url: Annotated[str, Field(db_type="VARCHAR", description="Full URL of the visited page")] = ""
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Page title")] = None
    visit_time: Annotated[str | None, Field(db_type="TIMESTAMP", description="Visit timestamp (UTC)")] = None
    visit_type: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Navigation type (link, typed, bookmark, redirect, ...)"),
    ] = None
    from_visit_id: Annotated[
        int | None,
        Field(db_type="BIGINT", description="Visit ID of the referring page (0 if none)"),
    ] = None

    @classmethod
    def extract(cls, client: str, *, cursor: Any = None, **_: Any) -> Iterator[dict[str, Any]]:
        last_time = cursor.last_value if cursor is not None else None

        con = sqlite3.connect(f"file:{client}?mode=ro", uri=True)
        try:
            con.row_factory = sqlite3.Row
            sql = """
                SELECT v.id, p.url, p.title, v.visit_date,
                       v.visit_type, v.from_visit
                FROM moz_historyvisits v
                JOIN moz_places p ON v.place_id = p.id
            """
            params: list[Any] = []
            if last_time:
                sql += " WHERE v.visit_date > ? "
                params.append(last_time)
            sql += " ORDER BY v.visit_date"

            for row in con.execute(sql, params):
                yield {
                    "id": row["id"],
                    "url": row["url"],
                    "title": row["title"] or None,
                    "visit_time": _firefox_time(row["visit_date"]),
                    "visit_type": _VISIT_TYPE.get(row["visit_type"], "other"),
                    "from_visit_id": row["from_visit"] or None,
                }
        finally:
            con.close()


class Bookmarks(DimensionTable):
    """Firefox bookmark, loaded as SCD2 to track additions and removals."""

    class _Meta:
        name = "bookmarks"
        display_name = "Bookmarks"
        description = "Firefox bookmarks with folder hierarchy."
        pk = ("id",)

    id: Annotated[int, Field(db_type="BIGINT", description="Firefox bookmark ID")] = 0
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Bookmark title")] = None
    url: Annotated[str | None, Field(db_type="VARCHAR", description="Bookmarked URL")] = None
    parent_title: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Parent folder name"),
    ] = None
    date_added: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When the bookmark was created (UTC)"),
    ] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        con = sqlite3.connect(f"file:{client}?mode=ro", uri=True)
        try:
            con.row_factory = sqlite3.Row
            sql = """
                SELECT b.id, b.title AS bookmark_title, p.url,
                       parent.title AS parent_title, b.dateAdded
                FROM moz_bookmarks b
                LEFT JOIN moz_places p ON b.fk = p.id
                LEFT JOIN moz_bookmarks parent ON b.parent = parent.id
                WHERE b.type = 1
            """
            for row in con.execute(sql):
                url = row["url"]
                if not url or url.startswith("place:"):
                    continue
                yield {
                    "id": row["id"],
                    "title": row["bookmark_title"] or None,
                    "url": url,
                    "parent_title": row["parent_title"] or None,
                    "date_added": _firefox_time(row["dateAdded"]),
                }
        finally:
            con.close()


TABLES: tuple[type[SourceTable], ...] = (Visits, Bookmarks)
