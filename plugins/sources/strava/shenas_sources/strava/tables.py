"""Strava raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class Activity:
    """Strava activity (run, ride, swim, ...) -- fetched as DetailedActivity."""

    __table__: ClassVar[str] = "activities"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

    id: Annotated[int, Field(db_type="BIGINT", description="Activity ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Activity name")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Activity description")] = None
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
    average_temp: Annotated[float | None, Field(db_type="DOUBLE", description="Average temperature (degC)")] = None
    kilojoules: Annotated[float | None, Field(db_type="DOUBLE", description="Total work (kJ)")] = None
    calories: Annotated[float | None, Field(db_type="DOUBLE", description="Calories (kcal)")] = None
    average_watts: Annotated[float | None, Field(db_type="DOUBLE", description="Average power (W)")] = None
    max_watts: Annotated[float | None, Field(db_type="DOUBLE", description="Max power (W)")] = None
    suffer_score: Annotated[float | None, Field(db_type="DOUBLE", description="Strava suffer score")] = None
    achievement_count: Annotated[int, Field(db_type="INTEGER", description="Achievement count")] = 0
    kudos_count: Annotated[int, Field(db_type="INTEGER", description="Kudos count")] = 0
    comment_count: Annotated[int, Field(db_type="INTEGER", description="Comment count")] = 0
    photo_count: Annotated[int, Field(db_type="INTEGER", description="Photo count")] = 0
    gear_id: Annotated[str | None, Field(db_type="VARCHAR", description="Associated gear ID")] = None
    device_name: Annotated[str | None, Field(db_type="VARCHAR", description="Recording device name")] = None
    trainer: Annotated[bool, Field(db_type="BOOLEAN", description="Indoor trainer")] = False
    commute: Annotated[bool, Field(db_type="BOOLEAN", description="Commute")] = False
    manual: Annotated[bool, Field(db_type="BOOLEAN", description="Manually entered")] = False


@dataclass
class Lap:
    """A single lap within an activity."""

    __table__: ClassVar[str] = "laps"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

    id: Annotated[int, Field(db_type="BIGINT", description="Lap ID")]
    activity_id: Annotated[int, Field(db_type="BIGINT", description="Parent activity ID")]
    lap_index: Annotated[int, Field(db_type="INTEGER", description="Lap index within activity")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Lap name")] = None
    start_date: Annotated[str | None, Field(db_type="TIMESTAMP", description="Lap start time (UTC)")] = None
    distance_m: Annotated[float | None, Field(db_type="DOUBLE", description="Distance (meters)")] = None
    moving_time_s: Annotated[int | None, Field(db_type="INTEGER", description="Moving time (seconds)")] = None
    elapsed_time_s: Annotated[int | None, Field(db_type="INTEGER", description="Elapsed time (seconds)")] = None
    elevation_gain_m: Annotated[float | None, Field(db_type="DOUBLE", description="Elevation gain (meters)")] = None
    average_speed_mps: Annotated[float | None, Field(db_type="DOUBLE", description="Average speed (m/s)")] = None
    max_speed_mps: Annotated[float | None, Field(db_type="DOUBLE", description="Max speed (m/s)")] = None
    average_heartrate: Annotated[float | None, Field(db_type="DOUBLE", description="Average HR (bpm)")] = None
    max_heartrate: Annotated[float | None, Field(db_type="DOUBLE", description="Max HR (bpm)")] = None
    average_watts: Annotated[float | None, Field(db_type="DOUBLE", description="Average power (W)")] = None
    average_cadence: Annotated[float | None, Field(db_type="DOUBLE", description="Average cadence")] = None


@dataclass
class Kudos:
    """An athlete who kudos'd an activity."""

    __table__: ClassVar[str] = "kudos"
    __pk__: ClassVar[tuple[str, ...]] = ("activity_id", "athlete_id")
    __kind__: ClassVar[TableKind] = "event"

    activity_id: Annotated[int, Field(db_type="BIGINT", description="Activity ID")]
    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID")]
    firstname: Annotated[str | None, Field(db_type="VARCHAR", description="First name")] = None
    lastname: Annotated[str | None, Field(db_type="VARCHAR", description="Last name")] = None


@dataclass
class Comment:
    """A comment on an activity."""

    __table__: ClassVar[str] = "comments"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

    id: Annotated[int, Field(db_type="BIGINT", description="Comment ID")]
    activity_id: Annotated[int, Field(db_type="BIGINT", description="Activity ID")]
    athlete_id: Annotated[int | None, Field(db_type="BIGINT", description="Commenter athlete ID")] = None
    athlete_name: Annotated[str | None, Field(db_type="VARCHAR", description="Commenter name")] = None
    text: Annotated[str | None, Field(db_type="TEXT", description="Comment text")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Created (UTC)")] = None


@dataclass
class Athlete:
    """Authenticated Strava athlete profile."""

    __table__: ClassVar[str] = "athlete"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID")]
    username: Annotated[str | None, Field(db_type="VARCHAR", description="Username")] = None
    firstname: Annotated[str | None, Field(db_type="VARCHAR", description="First name")] = None
    lastname: Annotated[str | None, Field(db_type="VARCHAR", description="Last name")] = None
    city: Annotated[str | None, Field(db_type="VARCHAR", description="City")] = None
    country: Annotated[str | None, Field(db_type="VARCHAR", description="Country")] = None
    sex: Annotated[str | None, Field(db_type="VARCHAR", description="Sex (M/F)")] = None
    weight_kg: Annotated[float | None, Field(db_type="DOUBLE", description="Weight (kg)")] = None
    ftp: Annotated[int | None, Field(db_type="INTEGER", description="Functional threshold power (W)")] = None


@dataclass
class AthleteStats:
    """Aggregated athlete stats (totals across run/ride/swim)."""

    __table__: ClassVar[str] = "athlete_stats"
    __pk__: ClassVar[tuple[str, ...]] = ("athlete_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID")]
    biggest_ride_distance_m: Annotated[float | None, Field(db_type="DOUBLE", description="Biggest ride distance")] = None
    biggest_climb_elevation_m: Annotated[float | None, Field(db_type="DOUBLE", description="Biggest climb elevation")] = None

    recent_run_count: Annotated[int, Field(db_type="INTEGER", description="Recent (28d) run count")] = 0
    recent_run_distance_m: Annotated[float, Field(db_type="DOUBLE", description="Recent run distance")] = 0.0
    recent_run_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="Recent run moving time")] = 0
    recent_ride_count: Annotated[int, Field(db_type="INTEGER", description="Recent (28d) ride count")] = 0
    recent_ride_distance_m: Annotated[float, Field(db_type="DOUBLE", description="Recent ride distance")] = 0.0
    recent_ride_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="Recent ride moving time")] = 0
    recent_swim_count: Annotated[int, Field(db_type="INTEGER", description="Recent (28d) swim count")] = 0
    recent_swim_distance_m: Annotated[float, Field(db_type="DOUBLE", description="Recent swim distance")] = 0.0
    recent_swim_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="Recent swim moving time")] = 0

    ytd_run_count: Annotated[int, Field(db_type="INTEGER", description="YTD run count")] = 0
    ytd_run_distance_m: Annotated[float, Field(db_type="DOUBLE", description="YTD run distance")] = 0.0
    ytd_run_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="YTD run moving time")] = 0
    ytd_ride_count: Annotated[int, Field(db_type="INTEGER", description="YTD ride count")] = 0
    ytd_ride_distance_m: Annotated[float, Field(db_type="DOUBLE", description="YTD ride distance")] = 0.0
    ytd_ride_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="YTD ride moving time")] = 0
    ytd_swim_count: Annotated[int, Field(db_type="INTEGER", description="YTD swim count")] = 0
    ytd_swim_distance_m: Annotated[float, Field(db_type="DOUBLE", description="YTD swim distance")] = 0.0
    ytd_swim_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="YTD swim moving time")] = 0

    all_run_count: Annotated[int, Field(db_type="INTEGER", description="All-time run count")] = 0
    all_run_distance_m: Annotated[float, Field(db_type="DOUBLE", description="All-time run distance")] = 0.0
    all_run_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="All-time run moving time")] = 0
    all_ride_count: Annotated[int, Field(db_type="INTEGER", description="All-time ride count")] = 0
    all_ride_distance_m: Annotated[float, Field(db_type="DOUBLE", description="All-time ride distance")] = 0.0
    all_ride_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="All-time ride moving time")] = 0
    all_swim_count: Annotated[int, Field(db_type="INTEGER", description="All-time swim count")] = 0
    all_swim_distance_m: Annotated[float, Field(db_type="DOUBLE", description="All-time swim distance")] = 0.0
    all_swim_moving_time_s: Annotated[int, Field(db_type="INTEGER", description="All-time swim moving time")] = 0


@dataclass
class AthleteZones:
    """Athlete heart rate and power zones (JSON blob)."""

    __table__: ClassVar[str] = "athlete_zones"
    __pk__: ClassVar[tuple[str, ...]] = ("athlete_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID")]
    heart_rate_zones: Annotated[str | None, Field(db_type="TEXT", description="HR zones JSON")] = None
    power_zones: Annotated[str | None, Field(db_type="TEXT", description="Power zones JSON")] = None


@dataclass
class Gear:
    """Bike or shoe with cumulative distance."""

    __table__: ClassVar[str] = "gear"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "counter"

    id: Annotated[str, Field(db_type="VARCHAR", description="Gear ID (e.g. 'b12345' or 'g6789')")]
    type: Annotated[str, Field(db_type="VARCHAR", description="'bike' or 'shoe'")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Gear name")] = None
    brand_name: Annotated[str | None, Field(db_type="VARCHAR", description="Brand name")] = None
    model_name: Annotated[str | None, Field(db_type="VARCHAR", description="Model name")] = None
    distance_m: Annotated[float | None, Field(db_type="DOUBLE", description="Cumulative distance (m)")] = None
    primary: Annotated[bool, Field(db_type="BOOLEAN", description="Marked as primary")] = False
    retired: Annotated[bool, Field(db_type="BOOLEAN", description="Retired")] = False
