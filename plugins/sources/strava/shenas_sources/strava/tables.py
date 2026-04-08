"""Strava raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field


@dataclass
class Activity:
    """Strava activity (run, ride, swim, ...)."""

    __table__: ClassVar[str] = "activities"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="BIGINT", description="Activity ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Activity name")] = None
    sport_type: Annotated[str | None, Field(db_type="VARCHAR", description="Sport type (Run, Ride, ...)")] = None
    start_date: Annotated[str | None, Field(db_type="TIMESTAMP", description="Start time (UTC)")] = None
    timezone: Annotated[str | None, Field(db_type="VARCHAR", description="Activity timezone")] = None
    distance_m: Annotated[float | None, Field(db_type="DOUBLE", description="Distance (meters)")] = None
    moving_time_s: Annotated[int | None, Field(db_type="INTEGER", description="Moving time (seconds)")] = None
    elapsed_time_s: Annotated[int | None, Field(db_type="INTEGER", description="Elapsed time (seconds)")] = None
    elevation_gain_m: Annotated[float | None, Field(db_type="DOUBLE", description="Elevation gain (meters)")] = None
    average_speed_mps: Annotated[float | None, Field(db_type="DOUBLE", description="Average speed (m/s)")] = None
    max_speed_mps: Annotated[float | None, Field(db_type="DOUBLE", description="Max speed (m/s)")] = None
    average_heartrate: Annotated[float | None, Field(db_type="DOUBLE", description="Average heart rate (bpm)")] = None
    max_heartrate: Annotated[float | None, Field(db_type="DOUBLE", description="Max heart rate (bpm)")] = None
    kilojoules: Annotated[float | None, Field(db_type="DOUBLE", description="Total work (kJ)")] = None
    calories: Annotated[float | None, Field(db_type="DOUBLE", description="Calories (kcal)")] = None
    average_watts: Annotated[float | None, Field(db_type="DOUBLE", description="Average power (W)")] = None
    max_watts: Annotated[float | None, Field(db_type="DOUBLE", description="Max power (W)")] = None
    suffer_score: Annotated[float | None, Field(db_type="DOUBLE", description="Strava suffer score")] = None
    trainer: Annotated[bool, Field(db_type="BOOLEAN", description="Indoor trainer")] = False
    commute: Annotated[bool, Field(db_type="BOOLEAN", description="Commute")] = False
    manual: Annotated[bool, Field(db_type="BOOLEAN", description="Manually entered")] = False


@dataclass
class Athlete:
    """Authenticated Strava athlete profile."""

    __table__: ClassVar[str] = "athlete"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID")]
    username: Annotated[str | None, Field(db_type="VARCHAR", description="Username")] = None
    firstname: Annotated[str | None, Field(db_type="VARCHAR", description="First name")] = None
    lastname: Annotated[str | None, Field(db_type="VARCHAR", description="Last name")] = None
    city: Annotated[str | None, Field(db_type="VARCHAR", description="City")] = None
    country: Annotated[str | None, Field(db_type="VARCHAR", description="Country")] = None
    sex: Annotated[str | None, Field(db_type="VARCHAR", description="Sex (M/F)")] = None
    weight_kg: Annotated[float | None, Field(db_type="DOUBLE", description="Weight (kg)")] = None
    ftp: Annotated[int | None, Field(db_type="INTEGER", description="Functional threshold power (W)")] = None
