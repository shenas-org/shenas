"""Strava source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. The class declares its schema fields, its
metadata, and the extraction logic in one place. Activities and Laps are
``IntervalTable`` (start + computed end). Kudos is ``M2MTable`` (athletes
who kudoed an activity), so when a kudo is removed the row's
``_dlt_valid_to`` is closed instead of leaving the link alive forever. Gear
is ``CounterTable`` so cumulative distance can be diffed across syncs.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import (
    CounterTable,
    EventTable,
    IntervalTable,
    M2MTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Helpers (shared by Activities/Laps/Kudos/Comments via the prefetched context)
# ---------------------------------------------------------------------------


def _q(value: Any) -> float | None:
    """Unwrap a stravalib pint Quantity (or numeric) into a plain float."""
    if value is None:
        return None
    magnitude = getattr(value, "magnitude", value)
    try:
        return float(magnitude)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    f = _q(value)
    return int(f) if f is not None else None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else str(value)


def _add_seconds(iso_start: str | None, seconds: int | None) -> str | None:
    """Compute an ISO end timestamp from start + duration in seconds."""
    if not iso_start or seconds is None:
        return None
    try:
        # fromisoformat handles trailing 'Z' since Python 3.11.
        dt = datetime.fromisoformat(iso_start)
        return (dt + timedelta(seconds=seconds)).isoformat()
    except (ValueError, TypeError):
        return None


def fetch_detailed_activities(client: Any, start_date: str = "30 days ago") -> list[Any]:
    """Fetch detailed activities since `start_date`.

    Each summary activity from get_activities() is followed by a get_activity()
    call to retrieve laps and rich metadata. Returned as a list so multiple
    Tables can iterate the same data without re-calling the API.
    """
    import pendulum

    from shenas_sources.core.utils import resolve_start_date

    after = pendulum.parse(resolve_start_date(start_date))
    detailed: list[Any] = []
    for summary in client.get_activities(after=after):
        detail = client.get_activity(summary.id, include_all_efforts=False)
        detailed.append(detail)
    return detailed


# ---------------------------------------------------------------------------
# Intervals
# ---------------------------------------------------------------------------


class Activities(IntervalTable):
    """A workout / activity (run, ride, swim, ...) -- start + computed end."""

    class _Meta:
        name = "activities"
        display_name = "Activities"
        description = "Strava workouts and activities, fetched as DetailedActivity."
        pk = ("id",)
        time_start = "start_date"
        time_end = "end_date"
        plot = (
            PlotHint("distance_m"),
            PlotHint("average_heartrate"),
            PlotHint("average_watts"),
            PlotHint("suffer_score"),
            PlotHint("elevation_gain_m"),
        )

    id: Annotated[int, Field(db_type="BIGINT", description="Activity ID", display_name="Activity ID")]
    name_: Annotated[str | None, Field(db_type="VARCHAR", description="Activity name", display_name="Activity Name")] = None
    activity_description: Annotated[
        str | None, Field(db_type="TEXT", description="Activity description", display_name="Description")
    ] = None
    sport_type: Annotated[
        str | None, Field(db_type="VARCHAR", description="Sport type (Run, Ride, ...)", display_name="Sport Type")
    ] = None
    start_date: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Start time (UTC)", display_name="Start Time")
    ] = None
    end_date: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Computed end (start + elapsed_time)", display_name="End Time")
    ] = None
    timezone: Annotated[str | None, Field(db_type="VARCHAR", description="Activity timezone", display_name="Timezone")] = None
    distance_m: Annotated[
        float | None, Field(db_type="DOUBLE", description="Distance (meters)", display_name="Distance", unit="m")
    ] = None
    moving_time_s: Annotated[
        int | None, Field(db_type="INTEGER", description="Moving time (seconds)", display_name="Moving Time", unit="s")
    ] = None
    elapsed_time_s: Annotated[
        int | None, Field(db_type="INTEGER", description="Elapsed time (seconds)", display_name="Elapsed Time", unit="s")
    ] = None
    elevation_gain_m: Annotated[
        float | None, Field(db_type="DOUBLE", description="Elevation gain (meters)", display_name="Elevation Gain", unit="m")
    ] = None
    average_speed_mps: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average speed (m/s)", display_name="Average Speed", unit="m/s")
    ] = None
    max_speed_mps: Annotated[
        float | None, Field(db_type="DOUBLE", description="Max speed (m/s)", display_name="Max Speed", unit="m/s")
    ] = None
    average_heartrate: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average heart rate (bpm)", display_name="Average HR", unit="bpm")
    ] = None
    max_heartrate: Annotated[
        float | None, Field(db_type="DOUBLE", description="Max heart rate (bpm)", display_name="Max HR", unit="bpm")
    ] = None
    average_temp: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Average temperature (degC)", display_name="Average Temp", unit="degC"),
    ] = None
    kilojoules: Annotated[
        float | None, Field(db_type="DOUBLE", description="Total work (kJ)", display_name="Total Work", unit="kJ")
    ] = None
    calories: Annotated[
        float | None, Field(db_type="DOUBLE", description="Calories (kcal)", display_name="Calories", unit="kcal")
    ] = None
    average_watts: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average power (W)", display_name="Average Power", unit="W")
    ] = None
    max_watts: Annotated[
        float | None, Field(db_type="DOUBLE", description="Max power (W)", display_name="Max Power", unit="W")
    ] = None
    suffer_score: Annotated[
        float | None, Field(db_type="DOUBLE", description="Strava suffer score", display_name="Suffer Score")
    ] = None
    achievement_count: Annotated[
        int, Field(db_type="INTEGER", description="Achievement count", display_name="Achievements")
    ] = 0
    kudos_count: Annotated[int, Field(db_type="INTEGER", description="Kudos count", display_name="Kudos")] = 0
    comment_count: Annotated[int, Field(db_type="INTEGER", description="Comment count", display_name="Comments")] = 0
    photo_count: Annotated[int, Field(db_type="INTEGER", description="Photo count", display_name="Photos")] = 0
    gear_id: Annotated[str | None, Field(db_type="VARCHAR", description="Associated gear ID", display_name="Gear ID")] = None
    device_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Recording device name", display_name="Device Name")
    ] = None
    trainer: Annotated[bool, Field(db_type="BOOLEAN", description="Indoor trainer", display_name="Trainer")] = False
    commute: Annotated[bool, Field(db_type="BOOLEAN", description="Commute", display_name="Commute")] = False
    manual: Annotated[bool, Field(db_type="BOOLEAN", description="Manually entered", display_name="Manual Entry")] = False

    @staticmethod
    def _activity_row(activity: Any) -> dict[str, Any]:
        start = _iso(getattr(activity, "start_date", None))
        elapsed = _i(getattr(activity, "elapsed_time", None))
        return {
            "id": int(activity.id),
            "name_": getattr(activity, "name", None),
            "activity_description": getattr(activity, "description", None),
            "sport_type": str(getattr(activity, "sport_type", "") or "") or None,
            "start_date": start,
            "end_date": _add_seconds(start, elapsed),
            "timezone": str(getattr(activity, "timezone", "") or "") or None,
            "distance_m": _q(getattr(activity, "distance", None)),
            "moving_time_s": _i(getattr(activity, "moving_time", None)),
            "elapsed_time_s": elapsed,
            "elevation_gain_m": _q(getattr(activity, "total_elevation_gain", None)),
            "average_speed_mps": _q(getattr(activity, "average_speed", None)),
            "max_speed_mps": _q(getattr(activity, "max_speed", None)),
            "average_heartrate": _q(getattr(activity, "average_heartrate", None)),
            "max_heartrate": _q(getattr(activity, "max_heartrate", None)),
            "average_temp": _q(getattr(activity, "average_temp", None)),
            "kilojoules": _q(getattr(activity, "kilojoules", None)),
            "calories": _q(getattr(activity, "calories", None)),
            "average_watts": _q(getattr(activity, "average_watts", None)),
            "max_watts": _q(getattr(activity, "max_watts", None)),
            "suffer_score": _q(getattr(activity, "suffer_score", None)),
            "achievement_count": int(getattr(activity, "achievement_count", 0) or 0),
            "kudos_count": int(getattr(activity, "kudos_count", 0) or 0),
            "comment_count": int(getattr(activity, "comment_count", 0) or 0),
            "photo_count": int(getattr(activity, "total_photo_count", 0) or 0),
            "gear_id": getattr(activity, "gear_id", None),
            "device_name": getattr(activity, "device_name", None),
            "trainer": bool(getattr(activity, "trainer", False)),
            "commute": bool(getattr(activity, "commute", False)),
            "manual": bool(getattr(activity, "manual", False)),
        }

    @classmethod
    def extract(cls, client: Any, *, detailed: list[Any] | None = None, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        for activity in detailed or []:
            yield cls._activity_row(activity)


class Laps(IntervalTable):
    """A single lap within an activity -- start + computed end."""

    class _Meta:
        name = "laps"
        display_name = "Laps"
        description = "Per-lap splits embedded in each detailed activity."
        pk = ("id",)
        time_start = "start_date"
        time_end = "end_date"
        plot = (PlotHint("distance_m"), PlotHint("average_speed_mps"), PlotHint("average_heartrate"))

    id: Annotated[int, Field(db_type="BIGINT", description="Lap ID", display_name="Lap ID")]
    activity_id: Annotated[int, Field(db_type="BIGINT", description="Parent activity ID", display_name="Activity ID")]
    lap_index: Annotated[int, Field(db_type="INTEGER", description="Lap index within activity", display_name="Lap Index")]
    name_: Annotated[str | None, Field(db_type="VARCHAR", description="Lap name", display_name="Lap Name")] = None
    start_date: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Lap start time (UTC)", display_name="Start Time")
    ] = None
    end_date: Annotated[str | None, Field(db_type="TIMESTAMP", description="Computed end", display_name="End Time")] = None
    distance_m: Annotated[
        float | None, Field(db_type="DOUBLE", description="Distance (meters)", display_name="Distance", unit="m")
    ] = None
    moving_time_s: Annotated[
        int | None, Field(db_type="INTEGER", description="Moving time (seconds)", display_name="Moving Time", unit="s")
    ] = None
    elapsed_time_s: Annotated[
        int | None, Field(db_type="INTEGER", description="Elapsed time (seconds)", display_name="Elapsed Time", unit="s")
    ] = None
    elevation_gain_m: Annotated[
        float | None, Field(db_type="DOUBLE", description="Elevation gain (meters)", display_name="Elevation Gain", unit="m")
    ] = None
    average_speed_mps: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average speed (m/s)", display_name="Average Speed", unit="m/s")
    ] = None
    max_speed_mps: Annotated[
        float | None, Field(db_type="DOUBLE", description="Max speed (m/s)", display_name="Max Speed", unit="m/s")
    ] = None
    average_heartrate: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average HR (bpm)", display_name="Average HR", unit="bpm")
    ] = None
    max_heartrate: Annotated[
        float | None, Field(db_type="DOUBLE", description="Max HR (bpm)", display_name="Max HR", unit="bpm")
    ] = None
    average_watts: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average power (W)", display_name="Average Power", unit="W")
    ] = None
    average_cadence: Annotated[
        float | None, Field(db_type="DOUBLE", description="Average cadence", display_name="Average Cadence", unit="rpm")
    ] = None

    @staticmethod
    def _lap_row(activity_id: int, lap: Any) -> dict[str, Any]:
        start = _iso(getattr(lap, "start_date", None))
        elapsed = _i(getattr(lap, "elapsed_time", None))
        return {
            "id": int(lap.id),
            "activity_id": activity_id,
            "lap_index": int(getattr(lap, "lap_index", 0) or 0),
            "name_": getattr(lap, "name", None),
            "start_date": start,
            "end_date": _add_seconds(start, elapsed),
            "distance_m": _q(getattr(lap, "distance", None)),
            "moving_time_s": _i(getattr(lap, "moving_time", None)),
            "elapsed_time_s": elapsed,
            "elevation_gain_m": _q(getattr(lap, "total_elevation_gain", None)),
            "average_speed_mps": _q(getattr(lap, "average_speed", None)),
            "max_speed_mps": _q(getattr(lap, "max_speed", None)),
            "average_heartrate": _q(getattr(lap, "average_heartrate", None)),
            "max_heartrate": _q(getattr(lap, "max_heartrate", None)),
            "average_watts": _q(getattr(lap, "average_watts", None)),
            "average_cadence": _q(getattr(lap, "average_cadence", None)),
        }

    @classmethod
    def extract(cls, client: Any, *, detailed: list[Any] | None = None, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        for d in detailed or []:
            for lap in getattr(d, "laps", None) or []:
                yield cls._lap_row(int(d.id), lap)


# ---------------------------------------------------------------------------
# m2m bridge: kudos
# ---------------------------------------------------------------------------


class Kudos(M2MTable):
    """Athletes who kudoed an activity. Pure m2m link, loaded as SCD2.

    Composite PK is (activity_id, athlete_id). The previous EventTable
    classification silently failed when a kudo was removed -- the link row
    stayed alive in DuckDB forever. SCD2 closes _dlt_valid_to on disappearance.
    """

    class _Meta:
        name = "kudos"
        display_name = "Kudos"
        description = "Per-activity kudos links (athlete -> activity)."
        pk = ("activity_id", "athlete_id")

    activity_id: Annotated[int, Field(db_type="BIGINT", description="Activity ID", display_name="Activity ID")]
    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID who kudoed", display_name="Athlete ID")]

    @classmethod
    def extract(
        cls,
        client: Any,
        *,
        detailed: list[Any] | None = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        for d in detailed or []:
            for k in client.get_activity_kudos(d.id):
                athlete_id = getattr(k, "id", None)
                if athlete_id is None:
                    continue
                yield {
                    "activity_id": int(d.id),
                    "athlete_id": int(athlete_id),
                }


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class Comments(EventTable):
    """Per-activity comments. Each comment has its own id and is immutable."""

    class _Meta:
        name = "comments"
        display_name = "Comments"
        description = "Comments left on activities by other athletes."
        pk = ("id",)
        time_at = "created_at"

    id: Annotated[int, Field(db_type="BIGINT", description="Comment ID", display_name="Comment ID")]
    activity_id: Annotated[int, Field(db_type="BIGINT", description="Activity ID", display_name="Activity ID")]
    athlete_id: Annotated[
        int | None, Field(db_type="BIGINT", description="Commenter athlete ID", display_name="Athlete ID")
    ] = None
    athlete_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Commenter name (denormalized)", display_name="Athlete Name")
    ] = None
    text: Annotated[str | None, Field(db_type="TEXT", description="Comment text", display_name="Comment Text")] = None
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Comment posted (UTC)", display_name="Created At")
    ] = None

    @classmethod
    def extract(
        cls,
        client: Any,
        *,
        detailed: list[Any] | None = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        for d in detailed or []:
            for c in client.get_activity_comments(d.id):
                commenter = getattr(c, "athlete", None)
                athlete_id = getattr(commenter, "id", None) if commenter else None
                firstname = getattr(commenter, "firstname", "") if commenter else ""
                lastname = getattr(commenter, "lastname", "") if commenter else ""
                full_name = f"{firstname} {lastname}".strip() or None
                yield {
                    "id": int(c.id),
                    "activity_id": int(d.id),
                    "athlete_id": int(athlete_id) if athlete_id is not None else None,
                    "athlete_name": full_name,
                    "text": getattr(c, "text", None),
                    "created_at": _iso(getattr(c, "created_at", None)),
                }


# ---------------------------------------------------------------------------
# Snapshots (loaded as SCD2)
# ---------------------------------------------------------------------------


class Athlete(SnapshotTable):
    """The authenticated Strava athlete profile."""

    class _Meta:
        name = "athlete"
        display_name = "Athlete"
        description = "Authenticated Strava athlete profile."
        pk = ("id",)
        entity_type = "human"
        entity_name_column = "username"
        entity_projection = {  # noqa: RUF012
            "city": {"entity_type": "city"},
            "country": {"entity_type": "country"},
        }

    id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID", display_name="Athlete ID")]
    username: Annotated[str | None, Field(db_type="VARCHAR", description="Username", display_name="Username")] = None
    firstname: Annotated[str | None, Field(db_type="VARCHAR", description="First name", display_name="First Name")] = None
    lastname: Annotated[str | None, Field(db_type="VARCHAR", description="Last name", display_name="Last Name")] = None
    city: Annotated[str | None, Field(db_type="VARCHAR", description="City", display_name="City")] = None
    country: Annotated[str | None, Field(db_type="VARCHAR", description="Country", display_name="Country")] = None
    sex: Annotated[str | None, Field(db_type="VARCHAR", description="Sex (M/F)", display_name="Sex")] = None
    weight_kg: Annotated[
        float | None, Field(db_type="DOUBLE", description="Weight (kg)", display_name="Weight", unit="kg")
    ] = None
    ftp: Annotated[int | None, Field(db_type="INTEGER", description="Functional threshold power (W)", display_name="FTP")] = (
        None
    )

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        a = client.get_athlete()
        yield {
            "id": int(a.id),
            "username": getattr(a, "username", None),
            "firstname": getattr(a, "firstname", None),
            "lastname": getattr(a, "lastname", None),
            "city": getattr(a, "city", None),
            "country": getattr(a, "country", None),
            "sex": getattr(a, "sex", None),
            "weight_kg": _q(getattr(a, "weight", None)),
            "ftp": _i(getattr(a, "ftp", None)),
        }


class AthleteStats(SnapshotTable):
    """Aggregated athlete totals (single row).

    NOTE: snapshot SCD2 versions on every change. Since YTD totals tick up
    after every activity, this will accumulate one version per sync. That's
    fine for now -- a future PR may split the cumulative columns out into a
    proper CounterTable, similar to the asset/plaid/crypto balance follow-up.
    """

    class _Meta:
        name = "athlete_stats"
        display_name = "Athlete Stats"
        description = "Recent / YTD / all-time totals for run, ride, swim."
        pk = ("athlete_id",)

    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID", display_name="Athlete ID")]
    biggest_ride_distance_m: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Biggest ride distance", display_name="Biggest Ride Distance", unit="m"),
    ] = None
    biggest_climb_elevation_m: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Biggest climb elevation", display_name="Biggest Climb Elevation", unit="m"),
    ] = None
    recent_run_count: Annotated[
        int, Field(db_type="INTEGER", description="Recent (28d) run count", display_name="Recent Run Count")
    ] = 0
    recent_run_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="Recent run distance", display_name="Recent Run Distance", unit="m")
    ] = 0.0
    recent_run_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="Recent run moving time", display_name="Recent Run Time", unit="s")
    ] = 0
    recent_ride_count: Annotated[
        int, Field(db_type="INTEGER", description="Recent (28d) ride count", display_name="Recent Ride Count")
    ] = 0
    recent_ride_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="Recent ride distance", display_name="Recent Ride Distance", unit="m")
    ] = 0.0
    recent_ride_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="Recent ride moving time", display_name="Recent Ride Time", unit="s")
    ] = 0
    recent_swim_count: Annotated[
        int, Field(db_type="INTEGER", description="Recent (28d) swim count", display_name="Recent Swim Count")
    ] = 0
    recent_swim_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="Recent swim distance", display_name="Recent Swim Distance", unit="m")
    ] = 0.0
    recent_swim_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="Recent swim moving time", display_name="Recent Swim Time", unit="s")
    ] = 0
    ytd_run_count: Annotated[int, Field(db_type="INTEGER", description="YTD run count", display_name="YTD Run Count")] = 0
    ytd_run_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="YTD run distance", display_name="YTD Run Distance", unit="m")
    ] = 0.0
    ytd_run_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="YTD run moving time", display_name="YTD Run Time", unit="s")
    ] = 0
    ytd_ride_count: Annotated[int, Field(db_type="INTEGER", description="YTD ride count", display_name="YTD Ride Count")] = 0
    ytd_ride_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="YTD ride distance", display_name="YTD Ride Distance", unit="m")
    ] = 0.0
    ytd_ride_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="YTD ride moving time", display_name="YTD Ride Time", unit="s")
    ] = 0
    ytd_swim_count: Annotated[int, Field(db_type="INTEGER", description="YTD swim count", display_name="YTD Swim Count")] = 0
    ytd_swim_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="YTD swim distance", display_name="YTD Swim Distance", unit="m")
    ] = 0.0
    ytd_swim_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="YTD swim moving time", display_name="YTD Swim Time", unit="s")
    ] = 0
    all_run_count: Annotated[
        int, Field(db_type="INTEGER", description="All-time run count", display_name="All-Time Run Count")
    ] = 0
    all_run_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="All-time run distance", display_name="All-Time Run Distance", unit="m")
    ] = 0.0
    all_run_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="All-time run moving time", display_name="All-Time Run Time", unit="s")
    ] = 0
    all_ride_count: Annotated[
        int, Field(db_type="INTEGER", description="All-time ride count", display_name="All-Time Ride Count")
    ] = 0
    all_ride_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="All-time ride distance", display_name="All-Time Ride Distance", unit="m")
    ] = 0.0
    all_ride_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="All-time ride moving time", display_name="All-Time Ride Time", unit="s")
    ] = 0
    all_swim_count: Annotated[
        int, Field(db_type="INTEGER", description="All-time swim count", display_name="All-Time Swim Count")
    ] = 0
    all_swim_distance_m: Annotated[
        float, Field(db_type="DOUBLE", description="All-time swim distance", display_name="All-Time Swim Distance", unit="m")
    ] = 0.0
    all_swim_moving_time_s: Annotated[
        int, Field(db_type="INTEGER", description="All-time swim moving time", display_name="All-Time Swim Time", unit="s")
    ] = 0

    @staticmethod
    def _totals(obj: Any, prefix: str) -> dict[str, Any]:
        return {
            f"{prefix}_count": int(getattr(obj, "count", 0) or 0),
            f"{prefix}_distance_m": _q(getattr(obj, "distance", None)) or 0.0,
            f"{prefix}_moving_time_s": _i(getattr(obj, "moving_time", None)) or 0,
        }

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        me = client.get_athlete()
        stats = client.get_athlete_stats(int(me.id))
        row: dict[str, Any] = {
            "athlete_id": int(me.id),
            "biggest_ride_distance_m": _q(getattr(stats, "biggest_ride_distance", None)),
            "biggest_climb_elevation_m": _q(getattr(stats, "biggest_climb_elevation_gain", None)),
        }
        for prefix, field in [
            ("recent_run", "recent_run_totals"),
            ("recent_ride", "recent_ride_totals"),
            ("recent_swim", "recent_swim_totals"),
            ("ytd_run", "ytd_run_totals"),
            ("ytd_ride", "ytd_ride_totals"),
            ("ytd_swim", "ytd_swim_totals"),
            ("all_run", "all_run_totals"),
            ("all_ride", "all_ride_totals"),
            ("all_swim", "all_swim_totals"),
        ]:
            row.update(cls._totals(getattr(stats, field, None), prefix))
        yield row


class AthleteZones(SnapshotTable):
    """HR + power zone configuration."""

    class _Meta:
        name = "athlete_zones"
        display_name = "Athlete Zones"
        description = "Heart-rate and power training zones."
        pk = ("athlete_id",)

    athlete_id: Annotated[int, Field(db_type="BIGINT", description="Athlete ID", display_name="Athlete ID")]
    heart_rate_zones: Annotated[str | None, Field(db_type="TEXT", description="HR zones JSON", display_name="HR Zones")] = None
    power_zones: Annotated[str | None, Field(db_type="TEXT", description="Power zones JSON", display_name="Power Zones")] = (
        None
    )

    @staticmethod
    def _zone_list(zone_obj: Any) -> str | None:
        if zone_obj is None:
            return None
        zones = getattr(zone_obj, "zones", None)
        if not zones:
            return None
        return json.dumps([{"min": getattr(z, "min", None), "max": getattr(z, "max", None)} for z in zones])

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        me = client.get_athlete()
        try:
            zones = client.get_athlete_zones()
        except Exception:
            return
        yield {
            "athlete_id": int(me.id),
            "heart_rate_zones": cls._zone_list(getattr(zones, "heart_rate", None)),
            "power_zones": cls._zone_list(getattr(zones, "power", None)),
        }


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------


class Gear(CounterTable):
    """Bikes and shoes with cumulative distance.

    Loaded as append-with-observed_at so consumers can compute deltas
    (kilometers ridden between two observations) instead of just reading
    the latest cumulative value.
    """

    class _Meta:
        name = "gear"
        display_name = "Gear"
        description = "Bikes and shoes with cumulative distance."
        pk = ("id",)
        counter_columns = ("distance_m",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Gear ID", display_name="Gear ID")]
    type: Annotated[str, Field(db_type="VARCHAR", description="'bike' or 'shoe'", display_name="Type")] = ""
    name_: Annotated[str | None, Field(db_type="VARCHAR", description="Gear name", display_name="Gear Name")] = None
    brand_name: Annotated[str | None, Field(db_type="VARCHAR", description="Brand name", display_name="Brand")] = None
    model_name: Annotated[str | None, Field(db_type="VARCHAR", description="Model name", display_name="Model")] = None
    distance_m: Annotated[
        float | None, Field(db_type="DOUBLE", description="Cumulative distance (m)", display_name="Distance", unit="m")
    ] = None
    primary: Annotated[bool, Field(db_type="BOOLEAN", description="Marked as primary", display_name="Primary")] = False
    retired: Annotated[bool, Field(db_type="BOOLEAN", description="Retired", display_name="Retired")] = False

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        me = client.get_athlete()
        for kind, items in (("bike", getattr(me, "bikes", None) or []), ("shoe", getattr(me, "shoes", None) or [])):
            for item in items:
                gear_id = getattr(item, "id", None)
                if gear_id is None:
                    continue
                try:
                    detail = client.get_gear(gear_id)
                except Exception:
                    detail = item
                yield {
                    "id": str(gear_id),
                    "type": kind,
                    "name_": getattr(detail, "name", None) or getattr(item, "name", None),
                    "brand_name": getattr(detail, "brand_name", None),
                    "model_name": getattr(detail, "model_name", None),
                    "distance_m": _q(getattr(detail, "distance", None)) or _q(getattr(item, "distance", None)),
                    "primary": bool(getattr(detail, "primary", False) or getattr(item, "primary", False)),
                    "retired": bool(getattr(detail, "retired", False) or getattr(item, "retired", False)),
                }


# ---------------------------------------------------------------------------
# Tables this source exposes, in sync order.
# ---------------------------------------------------------------------------


TABLES: tuple[type[SourceTable], ...] = (
    Activities,
    Laps,
    Kudos,
    Comments,
    Athlete,
    AthleteStats,
    AthleteZones,
    Gear,
)
