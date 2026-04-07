"""Garmin source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Garmin's API returns big nested dicts;
the dataclasses declare only the key fields and dlt's schema inference
fills in the rest.

- ``Activities`` is an ``IntervalTable`` (start + computed end) with
  cursor on ``startTimeLocal``.
- ``DailyStats``, ``Sleep``, ``Hrv``, ``Spo2``, ``BodyComposition`` are
  ``AggregateTable`` -- one row per calendar day -- with cursor on
  ``calendarDate``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

import pendulum

from shenas_plugins.core.field import Field
from shenas_sources.core.table import (
    AggregateTable,
    IntervalTable,
)
from shenas_sources.core.utils import date_range, is_empty_response

if TYPE_CHECKING:
    from collections.abc import Iterator

    from garminconnect import Garmin


class Activities(IntervalTable):
    """Garmin Connect activity summary.

    The Garmin API returns ``startTimeLocal`` and ``duration`` (seconds);
    we materialise ``end_time_local`` from start + duration so the row
    has both ends of the interval and the AS-OF / gantt-style queries
    work uniformly with the other interval tables.
    """

    name: ClassVar[str] = "activities"
    display_name: ClassVar[str] = "Activities"
    description: ClassVar[str | None] = "Activity summaries from Garmin Connect."
    pk: ClassVar[tuple[str, ...]] = ("activity_id",)
    time_start: ClassVar[str] = "startTimeLocal"
    time_end: ClassVar[str] = "end_time_local"
    cursor_column: ClassVar[str] = "startTimeLocal"

    activity_id: Annotated[str, Field(db_type="VARCHAR", description="Unique activity identifier")] = ""
    activityName: Annotated[str | None, Field(db_type="VARCHAR", description="Activity name")] = None  # noqa: N815
    startTimeLocal: Annotated[str | None, Field(db_type="TIMESTAMP", description="Local start time")] = None  # noqa: N815
    end_time_local: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Local end time (start + duration)"),
    ] = None
    activityType: Annotated[str | None, Field(db_type="VARCHAR", description="Activity type name")] = None  # noqa: N815
    distance: Annotated[float | None, Field(db_type="DOUBLE", description="Distance in meters")] = None
    duration: Annotated[float | None, Field(db_type="DOUBLE", description="Duration in seconds")] = None
    calories: Annotated[float | None, Field(db_type="DOUBLE", description="Calories burned")] = None
    averageHR: Annotated[float | None, Field(db_type="DOUBLE", description="Average heart rate")] = None  # noqa: N815
    maxHR: Annotated[float | None, Field(db_type="DOUBLE", description="Maximum heart rate")] = None  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        last = (cursor.last_value if cursor is not None else None) or start_date
        effective_start = str(last)[:10]
        end_date = pendulum.now().to_date_string()
        rows = client.get_activities_by_date(effective_start, end_date) or []
        for row in rows:
            row["activity_id"] = str(row["activityId"])
            row["end_time_local"] = _compute_end(row.get("startTimeLocal"), row.get("duration"))
            yield row


def _compute_end(start: str | None, duration_seconds: float | None) -> str | None:
    """Compute interval end as start + duration. Returns None if either is missing."""
    if not start or duration_seconds is None:
        return None
    try:
        return pendulum.parse(start).add(seconds=int(duration_seconds)).to_datetime_string()
    except Exception:
        return None


class _DailyAggregate(AggregateTable):
    """Common base for per-day Garmin aggregates keyed on calendarDate."""

    _abstract: ClassVar[bool] = True
    pk: ClassVar[tuple[str, ...]] = ("calendarDate",)
    time_at: ClassVar[str] = "calendarDate"
    cursor_column: ClassVar[str] = "calendarDate"


class DailyStats(_DailyAggregate):
    """Garmin daily stats summary."""

    name: ClassVar[str] = "daily_stats"
    display_name: ClassVar[str] = "Daily Stats"
    description: ClassVar[str | None] = "Per-day Garmin user summary (steps, calories, RHR)."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""  # noqa: N815
    totalSteps: Annotated[int | None, Field(db_type="INTEGER", description="Total steps")] = None  # noqa: N815
    totalDistanceMeters: Annotated[int | None, Field(db_type="INTEGER", description="Total distance in meters")] = None  # noqa: N815
    activeKilocalories: Annotated[float | None, Field(db_type="DOUBLE", description="Active kilocalories")] = None  # noqa: N815
    restingHeartRate: Annotated[int | None, Field(db_type="INTEGER", description="Resting heart rate")] = None  # noqa: N815
    maxHeartRate: Annotated[int | None, Field(db_type="INTEGER", description="Max heart rate")] = None  # noqa: N815
    stressQualifier: Annotated[str | None, Field(db_type="VARCHAR", description="Stress qualifier")] = None  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        last = cursor.last_value if cursor is not None else None
        for date in date_range(last or start_date):
            data = client.get_user_summary(date)
            if is_empty_response(data, sentinel_key="totalSteps"):
                continue
            yield data


class Sleep(_DailyAggregate):
    """Garmin sleep data."""

    name: ClassVar[str] = "sleep"
    display_name: ClassVar[str] = "Sleep"
    description: ClassVar[str | None] = "Per-day sleep data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        last = cursor.last_value if cursor is not None else None
        for date in date_range(last or start_date):
            data = client.get_sleep_data(date)
            if not data:
                continue
            data["calendarDate"] = date
            yield data


class Hrv(_DailyAggregate):
    """Garmin HRV data."""

    name: ClassVar[str] = "hrv"
    display_name: ClassVar[str] = "HRV"
    description: ClassVar[str | None] = "Per-day heart rate variability data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        last = cursor.last_value if cursor is not None else None
        for date in date_range(last or start_date):
            data = client.get_hrv_data(date)
            if not data:
                continue
            data["calendarDate"] = date
            yield data


class Spo2(_DailyAggregate):
    """Garmin SpO2 data."""

    name: ClassVar[str] = "spo2"
    display_name: ClassVar[str] = "SpO2"
    description: ClassVar[str | None] = "Per-day blood oxygen saturation data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        last = cursor.last_value if cursor is not None else None
        for date in date_range(last or start_date):
            data = client.get_spo2_data(date)
            if is_empty_response(data):
                continue
            yield data


class BodyComposition(AggregateTable):
    """Garmin body composition entry."""

    name: ClassVar[str] = "body_composition"
    display_name: ClassVar[str] = "Body Composition"
    description: ClassVar[str | None] = "Body composition entries (weight, body fat, etc)."
    pk: ClassVar[tuple[str, ...]] = ("samplePk",)

    samplePk: Annotated[int, Field(db_type="INTEGER", description="Sample primary key")] = 0  # noqa: N815

    @classmethod
    def extract(
        cls,
        client: Garmin,
        *,
        start_date: str = "30 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        end_date = pendulum.now().to_date_string()
        data = client.get_body_composition(start_date, end_date)
        if not data:
            return
        entries = data.get("dateWeightList") or data.get("totalAverage") or []
        if isinstance(entries, dict):
            entries = [entries]
        yield from entries


TABLES: tuple[type, ...] = (Activities, DailyStats, Sleep, Hrv, Spo2, BodyComposition)
