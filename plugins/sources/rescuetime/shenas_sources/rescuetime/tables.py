"""RescueTime source tables.

- ``DailySummary`` is an ``AggregateTable`` from the daily summary feed.
  Hours from the API are converted to seconds with ``_s`` suffix per the
  project's SI unit convention.
- ``Activities`` is an ``AggregateTable`` from the analytic data endpoint,
  one row per (date, activity) with duration and productivity score.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import AggregateTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.rescuetime.client import RescueTimeClient


def _hours_to_seconds(hours: float | None) -> float | None:
    if hours is None:
        return None
    return round(hours * 3600, 1)


class DailySummary(AggregateTable):
    """Daily productivity summary from RescueTime."""

    class _Meta:
        name = "daily_summary"
        display_name = "Daily Summary"
        description = "Daily productivity metrics from RescueTime."
        pk = ("date",)

    time_at: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    productivity_pulse: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="RescueTime productivity pulse (0-100)", display_name="Productivity Pulse"),
    ] = None
    total_s: Annotated[
        float | None, Field(db_type="DOUBLE", description="Total tracked time", display_name="Total Time", unit="s")
    ] = None
    very_productive_s: Annotated[
        float | None,
        Field(
            db_type="DOUBLE", description="Time on very productive activities", display_name="Very Productive Time", unit="s"
        ),
    ] = None
    productive_s: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Time on productive activities", display_name="Productive Time", unit="s"),
    ] = None
    neutral_s: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Time on neutral activities", display_name="Neutral Time", unit="s"),
    ] = None
    distracting_s: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Time on distracting activities", display_name="Distracting Time", unit="s"),
    ] = None
    very_distracting_s: Annotated[
        float | None,
        Field(
            db_type="DOUBLE", description="Time on very distracting activities", display_name="Very Distracting Time", unit="s"
        ),
    ] = None

    @classmethod
    def extract(cls, client: RescueTimeClient, **_: Any) -> Iterator[dict[str, Any]]:
        for day in client.get_daily_summary():
            yield {
                "date": day.get("date", ""),
                "productivity_pulse": day.get("productivity_pulse"),
                "total_s": _hours_to_seconds(day.get("total_hours")),
                "very_productive_s": _hours_to_seconds(day.get("very_productive_hours")),
                "productive_s": _hours_to_seconds(day.get("productive_hours")),
                "neutral_s": _hours_to_seconds(day.get("neutral_hours")),
                "distracting_s": _hours_to_seconds(day.get("distracting_hours")),
                "very_distracting_s": _hours_to_seconds(day.get("very_distracting_hours")),
            }


class Activities(AggregateTable):
    """Per-day, per-application activity breakdown from RescueTime."""

    class _Meta:
        name = "activities"
        display_name = "Activities"
        description = "Per-application time tracking from RescueTime."
        pk = ("date", "activity")

    time_at: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    activity: Annotated[str, Field(db_type="VARCHAR", description="Application or website name", display_name="Activity")] = ""
    category: Annotated[str | None, Field(db_type="VARCHAR", description="RescueTime category", display_name="Category")] = (
        None
    )
    duration_s: Annotated[
        float | None, Field(db_type="DOUBLE", description="Time spent", display_name="Duration", unit="s")
    ] = None
    productivity: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Productivity score (-2=very distracting to 2=very productive)",
            display_name="Productivity Score",
        ),
    ] = None

    @classmethod
    def extract(
        cls,
        client: RescueTimeClient,
        *,
        start_date: str = "30 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        begin = _resolve_start(start_date)
        end = datetime.now(UTC).strftime("%Y-%m-%d")
        for row in client.get_activities(begin, end):
            # row: [Date, Time Spent (seconds), Number of People, Activity, Category, Productivity]
            if len(row) < 6:
                continue
            yield {
                "date": str(row[0])[:10],
                "activity": row[3],
                "category": row[4],
                "duration_s": float(row[1]) if row[1] else None,
                "productivity": int(row[5]) if row[5] is not None else None,
            }


def _resolve_start(expr: str) -> str:
    """Convert '30 days ago' style expression to YYYY-MM-DD."""
    expr = expr.strip().lower()
    if expr and expr[0].isdigit():
        parts = expr.split()
        if len(parts) >= 2 and parts[1].startswith("day"):
            return (datetime.now(UTC) - timedelta(days=int(parts[0]))).strftime("%Y-%m-%d")
    return expr


TABLES: tuple[type[SourceTable], ...] = (DailySummary, Activities)
