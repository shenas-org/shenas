"""Chrome source tables.

Each table reads from Chrome's local SQLite ``History`` database. The
``client`` argument to ``extract()`` is the path to a temporary copy of
that database (copied to avoid Chrome's file lock).

- ``Visits`` is an ``IntervalTable`` keyed on Chrome's ``visits.id``.
  Joins ``visits`` + ``urls`` to include URL and title. End time is
  computed from visit_time + visit_duration.
- ``Downloads`` is an ``IntervalTable`` with start/end times.
- ``SearchTerms`` is an ``EventTable`` keyed on ``(url_id, term)``.
  Joins ``keyword_search_terms`` + ``urls`` for URL context.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import EventTable, IntervalTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Chrome epoch helpers
# ---------------------------------------------------------------------------

# Chrome stores timestamps as microseconds since 1601-01-01 00:00:00 UTC.
_CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)


def _chrome_time(us: int | None) -> str | None:
    """Convert a Chrome timestamp (microseconds since 1601-01-01) to ISO 8601."""
    if not us or us <= 0:
        return None
    try:
        dt = _CHROME_EPOCH + timedelta(microseconds=us)
        return dt.isoformat()
    except (OverflowError, OSError):
        return None


# Chrome encodes the navigation type in the low byte of visits.transition.
_TRANSITION_CORE: dict[int, str] = {
    0: "link",
    1: "typed",
    2: "auto_bookmark",
    3: "auto_subframe",
    4: "manual_subframe",
    5: "generated",
    6: "auto_toplevel",
    7: "form_submit",
    8: "reload",
    9: "keyword",
    10: "keyword_generated",
}

_DOWNLOAD_STATE: dict[int, str] = {
    0: "in_progress",
    1: "complete",
    2: "cancelled",
    3: "interrupted",
    4: "interrupted",
}


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Visits(IntervalTable):
    """Individual page visit from Chrome browsing history.

    Chrome stores ``visit_time`` and ``visit_duration`` (microseconds).
    We compute ``end_time`` as ``visit_time + visit_duration`` so the row
    has both ends of the interval.
    """

    class _Meta:
        name = "visits"
        display_name = "Visits"
        description = "Individual page visits from Chrome browsing history."
        pk = ("id",)

    time_start: ClassVar[str] = "visit_time"
    time_end: ClassVar[str] = "end_time"
    cursor_column: ClassVar[str] = "visit_time"

    id: Annotated[int, Field(db_type="BIGINT", description="Chrome visit ID")] = 0
    url: Annotated[str, Field(db_type="VARCHAR", description="Full URL of the visited page")] = ""
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Page title")] = None
    visit_time: Annotated[str | None, Field(db_type="TIMESTAMP", description="Visit start timestamp (UTC)")] = None
    end_time: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Visit end timestamp (start + duration, UTC)"),
    ] = None
    visit_duration_s: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Time spent on page", unit="s"),
    ] = None
    transition: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="How the user navigated here (link, typed, reload, ...)"),
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
                SELECT v.id, u.url, u.title, v.visit_time,
                       v.visit_duration, v.transition, v.from_visit
                FROM visits v
                JOIN urls u ON v.url = u.id
            """
            params: list[Any] = []
            if last_time:
                sql += " WHERE v.visit_time > ? "
                params.append(last_time)
            sql += " ORDER BY v.visit_time"

            for row in con.execute(sql, params):
                duration_us = row["visit_duration"]
                visit_time_us = row["visit_time"]
                yield {
                    "id": row["id"],
                    "url": row["url"],
                    "title": row["title"] or None,
                    "visit_time": _chrome_time(visit_time_us),
                    "end_time": _chrome_time(visit_time_us + duration_us) if duration_us else None,
                    "visit_duration_s": round(duration_us / 1_000_000, 3) if duration_us else None,
                    "transition": _TRANSITION_CORE.get(row["transition"] & 0xFF, "other"),
                    "from_visit_id": row["from_visit"] or None,
                }
        finally:
            con.close()


class Downloads(IntervalTable):
    """File download from Chrome."""

    class _Meta:
        name = "downloads"
        display_name = "Downloads"
        description = "File downloads recorded by Chrome."
        pk = ("id",)

    time_start: ClassVar[str] = "start_time"
    time_end: ClassVar[str] = "end_time"
    cursor_column: ClassVar[str] = "start_time"

    id: Annotated[int, Field(db_type="BIGINT", description="Chrome download ID")] = 0
    tab_url: Annotated[str | None, Field(db_type="VARCHAR", description="URL of the tab that initiated the download")] = None
    target_path: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Local file path where the download was saved"),
    ] = None
    start_time: Annotated[str | None, Field(db_type="TIMESTAMP", description="Download start timestamp (UTC)")] = None
    end_time: Annotated[str | None, Field(db_type="TIMESTAMP", description="Download end timestamp (UTC)")] = None
    total_bytes: Annotated[int | None, Field(db_type="BIGINT", description="Total file size", unit="bytes")] = None
    received_bytes: Annotated[int | None, Field(db_type="BIGINT", description="Bytes received so far", unit="bytes")] = None
    state: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Download state (complete, cancelled, interrupted, in_progress)"),
    ] = None
    mime_type: Annotated[str | None, Field(db_type="VARCHAR", description="MIME type of the downloaded file")] = None
    original_mime_type: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Original MIME type before any content-type sniffing"),
    ] = None

    @classmethod
    def extract(cls, client: str, *, cursor: Any = None, **_: Any) -> Iterator[dict[str, Any]]:
        last_time = cursor.last_value if cursor is not None else None

        con = sqlite3.connect(f"file:{client}?mode=ro", uri=True)
        try:
            con.row_factory = sqlite3.Row
            sql = """
                SELECT id, tab_url, target_path, start_time, end_time,
                       total_bytes, received_bytes, state,
                       mime_type, original_mime_type
                FROM downloads
            """
            params: list[Any] = []
            if last_time:
                sql += " WHERE start_time > ? "
                params.append(last_time)
            sql += " ORDER BY start_time"

            for row in con.execute(sql, params):
                yield {
                    "id": row["id"],
                    "tab_url": row["tab_url"] or None,
                    "target_path": row["target_path"] or None,
                    "start_time": _chrome_time(row["start_time"]),
                    "end_time": _chrome_time(row["end_time"]),
                    "total_bytes": row["total_bytes"] if row["total_bytes"] and row["total_bytes"] > 0 else None,
                    "received_bytes": row["received_bytes"] if row["received_bytes"] and row["received_bytes"] > 0 else None,
                    "state": _DOWNLOAD_STATE.get(row["state"], "unknown"),
                    "mime_type": row["mime_type"] or None,
                    "original_mime_type": row["original_mime_type"] or None,
                }
        finally:
            con.close()


class SearchTerms(EventTable):
    """Search term entered in Chrome's address bar or search engine."""

    class _Meta:
        name = "search_terms"
        display_name = "Search Terms"
        description = "Search queries entered via Chrome's address bar or search engines."
        pk = ("url_id", "term")

    time_at: ClassVar[str] = "last_visit_time"

    url_id: Annotated[int, Field(db_type="BIGINT", description="Chrome URL ID linking to the search result page")] = 0
    term: Annotated[str, Field(db_type="VARCHAR", description="The search query text")] = ""
    normalized_term: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Lowercased/normalized form of the search term"),
    ] = None
    url: Annotated[str | None, Field(db_type="VARCHAR", description="URL of the search result page")] = None
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Title of the search result page")] = None
    last_visit_time: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Last time this search URL was visited (UTC)"),
    ] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        con = sqlite3.connect(f"file:{client}?mode=ro", uri=True)
        try:
            con.row_factory = sqlite3.Row
            sql = """
                SELECT k.url_id, k.term, k.normalized_term,
                       u.url, u.title, u.last_visit_time
                FROM keyword_search_terms k
                JOIN urls u ON k.url_id = u.id
                ORDER BY u.last_visit_time
            """
            for row in con.execute(sql):
                yield {
                    "url_id": row["url_id"],
                    "term": row["term"],
                    "normalized_term": row["normalized_term"] or None,
                    "url": row["url"] or None,
                    "title": row["title"] or None,
                    "last_visit_time": _chrome_time(row["last_visit_time"]),
                }
        finally:
            con.close()


TABLES: tuple[type[SourceTable], ...] = (Visits, Downloads, SearchTerms)
