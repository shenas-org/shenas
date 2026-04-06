"""Garmin raw table schemas.

Garmin resources yield raw API dicts with many nested fields.
These dataclasses define only the key fields -- dlt will handle
extra fields automatically via its schema inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_datasets.core.field import Field


@dataclass
class Activity:
    """Garmin Connect activity summary."""

    __table__: ClassVar[str] = "activities"
    __pk__: ClassVar[tuple[str, ...]] = ("activity_id",)

    activity_id: Annotated[str, Field(db_type="VARCHAR", description="Unique activity identifier")]
    activityName: Annotated[str | None, Field(db_type="VARCHAR", description="Activity name")] = None  # noqa: N815
    startTimeLocal: Annotated[str | None, Field(db_type="TIMESTAMP", description="Local start time")] = None  # noqa: N815
    activityType: Annotated[str | None, Field(db_type="VARCHAR", description="Activity type name")] = None  # noqa: N815
    distance: Annotated[float | None, Field(db_type="DOUBLE", description="Distance in meters")] = None
    duration: Annotated[float | None, Field(db_type="DOUBLE", description="Duration in seconds")] = None
    calories: Annotated[float | None, Field(db_type="DOUBLE", description="Calories burned")] = None
    averageHR: Annotated[float | None, Field(db_type="DOUBLE", description="Average heart rate")] = None  # noqa: N815
    maxHR: Annotated[float | None, Field(db_type="DOUBLE", description="Maximum heart rate")] = None  # noqa: N815


@dataclass
class DailyStat:
    """Garmin daily stats summary."""

    __table__: ClassVar[str] = "daily_stats"
    __pk__: ClassVar[tuple[str, ...]] = ("calendarDate",)

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")]  # noqa: N815
    totalSteps: Annotated[int | None, Field(db_type="INTEGER", description="Total steps")] = None  # noqa: N815
    totalDistanceMeters: Annotated[int | None, Field(db_type="INTEGER", description="Total distance in meters")] = None  # noqa: N815
    activeKilocalories: Annotated[float | None, Field(db_type="DOUBLE", description="Active kilocalories")] = None  # noqa: N815
    restingHeartRate: Annotated[int | None, Field(db_type="INTEGER", description="Resting heart rate")] = None  # noqa: N815
    maxHeartRate: Annotated[int | None, Field(db_type="INTEGER", description="Max heart rate")] = None  # noqa: N815
    stressQualifier: Annotated[str | None, Field(db_type="VARCHAR", description="Stress qualifier")] = None  # noqa: N815


@dataclass
class Sleep:
    """Garmin sleep data."""

    __table__: ClassVar[str] = "sleep"
    __pk__: ClassVar[tuple[str, ...]] = ("calendarDate",)

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")]  # noqa: N815


@dataclass
class HRV:
    """Garmin HRV data."""

    __table__: ClassVar[str] = "hrv"
    __pk__: ClassVar[tuple[str, ...]] = ("calendarDate",)

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")]  # noqa: N815


@dataclass
class SpO2:
    """Garmin SpO2 data."""

    __table__: ClassVar[str] = "spo2"
    __pk__: ClassVar[tuple[str, ...]] = ("calendarDate",)

    calendarDate: Annotated[str, Field(db_type="DATE", description="Calendar date")]  # noqa: N815


@dataclass
class BodyComposition:
    """Garmin body composition entry."""

    __table__: ClassVar[str] = "body_composition"
    __pk__: ClassVar[tuple[str, ...]] = ("samplePk",)

    samplePk: Annotated[int, Field(db_type="INTEGER", description="Sample primary key")]  # noqa: N815
