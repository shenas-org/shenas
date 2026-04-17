"""Withings source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``.

- ``Measurements`` is an ``EventTable`` keyed on ``grpid``. Each
  measurement group (a single weigh-in, BP reading, etc.) yields one
  row with type codes flattened to named columns.
- ``SleepSummary`` and ``DailyActivity`` are ``AggregateTable`` keyed
  on ``date`` with cursor-based incremental sync.
- ``Devices`` is a ``SnapshotTable`` (SCD2) tracking connected
  Withings hardware over time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

import pendulum

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import (
    AggregateTable,
    EventTable,
    SnapshotTable,
    SourceTable,
)
from shenas_sources.core.utils import resolve_start_date

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.withings.client import WithingsClient


class Measurements(EventTable):
    """Body measurements (weight, fat, BP, SpO2, etc.).

    Each measurement group from the Withings API becomes one row with
    type codes flattened to named columns and values scaled by their
    unit exponent.
    """

    class _Meta:
        name = "measurements"
        display_name = "Measurements"
        description = "Body measurements from Withings scales, BP monitors, and other devices."
        pk = ("grpid",)
        time_at = "created_at"
        plot = (
            PlotHint("weight_kg"),
            PlotHint("fat_mass_kg"),
            PlotHint("systolic_bp"),
            PlotHint("diastolic_bp"),
            PlotHint("heart_pulse"),
            PlotHint("spo2_pct"),
        )

    grpid: Annotated[int, Field(db_type="BIGINT", description="Measurement group ID", display_name="Group ID")]
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Measurement timestamp", display_name="Measured At")
    ] = None
    weight_kg: Annotated[
        float | None, Field(db_type="DOUBLE", description="Body weight", display_name="Weight", unit="kg")
    ] = None
    fat_mass_kg: Annotated[
        float | None, Field(db_type="DOUBLE", description="Fat mass", display_name="Fat Mass", unit="kg")
    ] = None
    fat_free_mass_kg: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Fat-free mass", display_name="Fat-Free Mass", unit="kg"),
    ] = None
    fat_ratio_pct: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Body fat percentage", display_name="Body Fat", unit="percent"),
    ] = None
    muscle_mass_kg: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Muscle mass", display_name="Muscle Mass", unit="kg"),
    ] = None
    bone_mass_kg: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Bone mass", display_name="Bone Mass", unit="kg"),
    ] = None
    body_temperature_degc: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Body temperature", display_name="Body Temp", unit="degC"),
    ] = None
    diastolic_bp: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Diastolic blood pressure", display_name="Diastolic BP"),
    ] = None
    systolic_bp: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Systolic blood pressure", display_name="Systolic BP"),
    ] = None
    heart_pulse: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Heart rate at measurement time", display_name="Heart Rate", unit="bpm"),
    ] = None
    spo2_pct: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Blood oxygen saturation", display_name="SpO2", unit="percent"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: WithingsClient,
        *,
        start_date: str = "30 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        start = resolve_start_date(start_date)
        start_epoch = int(pendulum.parse(start).timestamp())  # ty: ignore[unresolved-attribute]
        end_epoch = int(pendulum.now().timestamp())
        yield from client.get_measurements(start_epoch, end_epoch)


class SleepSummary(AggregateTable):
    """Daily sleep summary from Withings sleep tracking devices."""

    class _Meta:
        name = "sleep_summary"
        display_name = "Sleep Summary"
        description = "Per-night sleep summary from Withings Sleep Mat or ScanWatch."
        pk = ("date",)
        time_at = "date"
        plot = (
            PlotHint("total_sleep_duration_s"),
            PlotHint("deep_sleep_duration_s"),
            PlotHint("rem_sleep_duration_s"),
            PlotHint("sleep_score"),
        )

    cursor_column: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Night date", display_name="Date")] = ""
    total_sleep_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Total sleep duration", display_name="Total Sleep", unit="s"),
    ] = None
    deep_sleep_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Deep sleep duration", display_name="Deep Sleep", unit="s"),
    ] = None
    rem_sleep_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="REM sleep duration", display_name="REM Sleep", unit="s"),
    ] = None
    light_sleep_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Light sleep duration", display_name="Light Sleep", unit="s"),
    ] = None
    wakeup_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Time awake during the night", display_name="Wakeup Time", unit="s"),
    ] = None
    sleep_score: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Sleep score", display_name="Sleep Score", value_range=(0, 100)),
    ] = None
    breathing_disturbances_intensity: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Breathing disturbances intensity index", display_name="Breathing Disturbances"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: WithingsClient,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        cursor_val = cursor.last_value if cursor is not None else None
        last_str = str(cursor_val)[:10] if cursor_val else start_date
        start = resolve_start_date(last_str)
        end = pendulum.now().to_date_string()
        for row in client.get_sleep_summary(start, end):
            yield {
                "date": row.get("date"),
                "total_sleep_duration_s": row.get("data", {}).get("total_sleep_duration") or row.get("total_sleep_duration"),
                "deep_sleep_duration_s": row.get("data", {}).get("deepsleepduration") or row.get("deepsleepduration"),
                "rem_sleep_duration_s": row.get("data", {}).get("remsleepduration") or row.get("remsleepduration"),
                "light_sleep_duration_s": row.get("data", {}).get("lightsleepduration") or row.get("lightsleepduration"),
                "wakeup_duration_s": row.get("data", {}).get("wakeupduration") or row.get("wakeupduration"),
                "sleep_score": row.get("data", {}).get("sleep_score") or row.get("sleep_score"),
                "breathing_disturbances_intensity": (
                    row.get("data", {}).get("breathing_disturbances_intensity") or row.get("breathing_disturbances_intensity")
                ),
            }


class DailyActivity(AggregateTable):
    """Daily activity summary (steps, distance, calories)."""

    class _Meta:
        name = "daily_activity"
        display_name = "Daily Activity"
        description = "Per-day activity summary from Withings wearables."
        pk = ("date",)
        time_at = "date"
        plot = (
            PlotHint("steps"),
            PlotHint("distance_m"),
            PlotHint("active_calories_kcal"),
            PlotHint("total_calories_kcal"),
        )

    cursor_column: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    steps: Annotated[int | None, Field(db_type="INTEGER", description="Total steps", display_name="Steps")] = None
    distance_m: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Total distance", display_name="Distance", unit="m"),
    ] = None
    active_calories_kcal: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Active calories burned", display_name="Active Calories", unit="kcal"),
    ] = None
    total_calories_kcal: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Total calories burned", display_name="Total Calories", unit="kcal"),
    ] = None
    soft_activity_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Low-intensity activity duration", display_name="Light Activity", unit="s"),
    ] = None
    moderate_activity_duration_s: Annotated[
        int | None,
        Field(
            db_type="INTEGER", description="Moderate-intensity activity duration", display_name="Moderate Activity", unit="s"
        ),
    ] = None
    intense_activity_duration_s: Annotated[
        int | None,
        Field(db_type="INTEGER", description="High-intensity activity duration", display_name="Intense Activity", unit="s"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: WithingsClient,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        cursor_val = cursor.last_value if cursor is not None else None
        last_str = str(cursor_val)[:10] if cursor_val else start_date
        start = resolve_start_date(last_str)
        end = pendulum.now().to_date_string()
        for row in client.get_activity(start, end):
            yield {
                "date": row.get("date"),
                "steps": row.get("steps"),
                "distance_m": row.get("distance"),
                "active_calories_kcal": row.get("calories"),
                "total_calories_kcal": row.get("totalcalories"),
                "soft_activity_duration_s": row.get("soft"),
                "moderate_activity_duration_s": row.get("moderate"),
                "intense_activity_duration_s": row.get("intense"),
            }


class Devices(SnapshotTable):
    """Connected Withings devices. SCD2 tracks firmware updates and battery changes."""

    class _Meta:
        name = "devices"
        display_name = "Devices"
        description = "Connected Withings health devices."
        pk = ("deviceid",)

    deviceid: Annotated[str, Field(db_type="VARCHAR", description="Device identifier", display_name="Device ID")]
    type_: Annotated[str | None, Field(db_type="VARCHAR", description="Device type", display_name="Device Type")] = None
    model: Annotated[str | None, Field(db_type="VARCHAR", description="Device model name", display_name="Model")] = None
    battery: Annotated[str | None, Field(db_type="VARCHAR", description="Battery level indicator", display_name="Battery")] = (
        None
    )
    firmware: Annotated[str | None, Field(db_type="VARCHAR", description="Firmware version", display_name="Firmware")] = None

    @classmethod
    def extract(cls, client: WithingsClient, **_: Any) -> Iterator[dict[str, Any]]:
        for d in client.get_devices():
            yield {
                "deviceid": str(d.get("deviceid") or d.get("device_id") or ""),
                "type_": d.get("type"),
                "model": d.get("model"),
                "battery": d.get("battery"),
                "firmware": d.get("fw"),
            }


TABLES: tuple[type[SourceTable], ...] = (Measurements, SleepSummary, DailyActivity, Devices)
