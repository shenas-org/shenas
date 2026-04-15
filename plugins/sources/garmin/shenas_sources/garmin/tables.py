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

Field names mirror the Garmin API (camelCase). The file-level
``ruff: noqa: N815`` silences PEP-8 mixedCase complaints across the
whole module so individual ``# noqa`` comments don't have to be
maintained on every column.
"""

# ruff: noqa: N815

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

import pendulum

from app.table import Field
from shenas_sources.core.table import (
    AggregateTable,
    IntervalTable,
    SourceTable,
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

    class _Meta:
        name = "activities"
        display_name = "Activities"
        description = "Activity summaries from Garmin Connect."
        pk = ("activity_id",)
        time_start = "startTimeLocal"
        time_end = "end_time_local"

    cursor_column: ClassVar[str] = "startTimeLocal"

    activity_id: Annotated[
        str, Field(db_type="VARCHAR", description="Unique activity identifier", display_name="Activity ID")
    ] = ""
    activityName: Annotated[
        str | None, Field(db_type="VARCHAR", description="Activity name", display_name="Activity Name")
    ] = None
    startTimeLocal: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Local start time", display_name="Start Time")
    ] = None
    end_time_local: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Local end time (start + duration)", display_name="End Time"),
    ] = None
    activityType: Annotated[
        str | None, Field(db_type="VARCHAR", description="Activity type name", display_name="Activity Type")
    ] = None
    distance: Annotated[float | None, Field(db_type="DOUBLE", description="Distance in meters", display_name="Distance")] = (
        None
    )
    duration: Annotated[float | None, Field(db_type="DOUBLE", description="Duration in seconds", display_name="Duration")] = (
        None
    )
    calories: Annotated[
        float | None, Field(db_type="DOUBLE", description="Calories burned", display_name="Calories", unit="kcal")
    ] = None
    averageHR: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average heart rate", display_name="Average HR")
    ] = None
    maxHR: Annotated[float | None, Field(db_type="DOUBLE", description="Maximum heart rate", display_name="Max HR")] = None

    @staticmethod
    def _compute_end(start: str | None, duration_seconds: float | None) -> str | None:
        """Compute interval end as start + duration. Returns None if either is missing."""
        if not start or duration_seconds is None:
            return None
        try:
            return pendulum.parse(start).add(seconds=int(duration_seconds)).to_datetime_string()  # ty: ignore[unresolved-attribute, unknown-argument]
        except Exception:
            return None

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
            row["end_time_local"] = cls._compute_end(row.get("startTimeLocal"), row.get("duration"))
            yield row


class _DailyAggregate(AggregateTable):
    """Common base for per-day Garmin aggregates keyed on calendarDate."""

    _abstract: ClassVar[bool] = True

    class _Meta:
        pk = ("calendarDate",)
        time_at = "calendarDate"

    cursor_column: ClassVar[str] = "calendarDate"


class DailyStats(_DailyAggregate):
    """Garmin daily stats summary."""

    class _Meta:
        name = "daily_stats"
        display_name = "Daily Stats"
        description = "Per-day Garmin user summary (steps, calories, RHR)."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    totalSteps: Annotated[int | None, Field(db_type="INTEGER", description="Total steps", display_name="Total Steps")] = None
    totalDistanceMeters: Annotated[
        int | None, Field(db_type="INTEGER", description="Total distance in meters", display_name="Total Distance", unit="m")
    ] = None
    activeKilocalories: Annotated[
        float | None, Field(db_type="DOUBLE", description="Active kilocalories", display_name="Active Calories", unit="kcal")
    ] = None
    restingHeartRate: Annotated[
        int | None, Field(db_type="INTEGER", description="Resting heart rate", display_name="Resting HR", unit="bpm")
    ] = None
    maxHeartRate: Annotated[
        int | None, Field(db_type="INTEGER", description="Max heart rate", display_name="Max HR", unit="bpm")
    ] = None
    stressQualifier: Annotated[
        str | None, Field(db_type="VARCHAR", description="Stress qualifier", display_name="Stress Qualifier")
    ] = None

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

    class _Meta:
        name = "sleep"
        display_name = "Sleep"
        description = "Per-day sleep data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""

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

    class _Meta:
        name = "hrv"
        display_name = "HRV"
        description = "Per-day heart rate variability data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""

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

    class _Meta:
        name = "spo2"
        display_name = "SpO2"
        description = "Per-day blood oxygen saturation data."

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""

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

    class _Meta:
        name = "body_composition"
        display_name = "Body Composition"
        description = "Body composition entries (weight, body fat, etc)."
        pk = ("samplePk",)

    samplePk: Annotated[int, Field(db_type="INTEGER", description="Sample primary key", display_name="Sample ID")] = 0

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


TABLES: tuple[type[SourceTable], ...] = (Activities, DailyStats, Sleep, Hrv, Spo2, BodyComposition)
