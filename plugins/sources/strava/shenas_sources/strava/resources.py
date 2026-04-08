"""Strava dlt resources -- activities (with detail), laps, kudos, comments,
athlete, athlete_stats, athlete_zones, gear."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.core.utils import resolve_start_date
from shenas_sources.strava.tables import (
    Activity,
    Athlete,
    AthleteStats,
    AthleteZones,
    Comment,
    Gear,
    Kudos,
    Lap,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime


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


def _activity_row(activity: Any) -> dict[str, Any]:
    """Map a stravalib DetailedActivity (or summary) to a flat dict."""
    return {
        "id": int(activity.id),
        "name": getattr(activity, "name", None),
        "description": getattr(activity, "description", None),
        "sport_type": str(getattr(activity, "sport_type", "") or "") or None,
        "start_date": _iso(getattr(activity, "start_date", None)),
        "timezone": str(getattr(activity, "timezone", "") or "") or None,
        "distance_m": _q(getattr(activity, "distance", None)),
        "moving_time_s": _i(getattr(activity, "moving_time", None)),
        "elapsed_time_s": _i(getattr(activity, "elapsed_time", None)),
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


def _lap_row(activity_id: int, lap: Any) -> dict[str, Any]:
    return {
        "id": int(lap.id),
        "activity_id": activity_id,
        "lap_index": int(getattr(lap, "lap_index", 0) or 0),
        "name": getattr(lap, "name", None),
        "start_date": _iso(getattr(lap, "start_date", None)),
        "distance_m": _q(getattr(lap, "distance", None)),
        "moving_time_s": _i(getattr(lap, "moving_time", None)),
        "elapsed_time_s": _i(getattr(lap, "elapsed_time", None)),
        "elevation_gain_m": _q(getattr(lap, "total_elevation_gain", None)),
        "average_speed_mps": _q(getattr(lap, "average_speed", None)),
        "max_speed_mps": _q(getattr(lap, "max_speed", None)),
        "average_heartrate": _q(getattr(lap, "average_heartrate", None)),
        "max_heartrate": _q(getattr(lap, "max_heartrate", None)),
        "average_watts": _q(getattr(lap, "average_watts", None)),
        "average_cadence": _q(getattr(lap, "average_cadence", None)),
    }


def fetch_detailed_activities(client: Any, start_date: str = "30 days ago") -> list[Any]:
    """Fetch detailed activities since `start_date`.

    Each summary activity from get_activities() is followed by a get_activity()
    call to retrieve laps and rich metadata. Returned as a list so multiple
    dlt resources can iterate the same data without re-calling the API.
    """
    import pendulum

    after: datetime = pendulum.parse(resolve_start_date(start_date))
    detailed: list[Any] = []
    for summary in client.get_activities(after=after):
        detail = client.get_activity(summary.id, include_all_efforts=False)
        detailed.append(detail)
    return detailed


@dlt.resource(
    name="activities",
    write_disposition="merge",
    primary_key=list(Activity.__pk__),
    columns=dataclass_to_dlt_columns(Activity),
)
def activities(detailed: list[Any]) -> Iterator[dict[str, Any]]:
    """Yield activity rows from a pre-fetched list of DetailedActivity."""
    for d in detailed:
        yield _activity_row(d)


@dlt.resource(
    name="laps",
    write_disposition="merge",
    primary_key=list(Lap.__pk__),
    columns=dataclass_to_dlt_columns(Lap),
)
def laps(detailed: list[Any]) -> Iterator[dict[str, Any]]:
    """Yield lap rows from the laps embedded in each DetailedActivity."""
    for d in detailed:
        for lap in getattr(d, "laps", None) or []:
            yield _lap_row(int(d.id), lap)


@dlt.resource(
    name="kudos",
    write_disposition="merge",
    primary_key=list(Kudos.__pk__),
    columns=dataclass_to_dlt_columns(Kudos),
)
def kudos(client: Any, detailed: list[Any]) -> Iterator[dict[str, Any]]:
    """For each detailed activity, fetch and yield athletes who kudos'd."""
    for d in detailed:
        for k in client.get_activity_kudos(d.id):
            athlete_id = getattr(k, "id", None)
            if athlete_id is None:
                continue
            yield {
                "activity_id": int(d.id),
                "athlete_id": int(athlete_id),
                "firstname": getattr(k, "firstname", None),
                "lastname": getattr(k, "lastname", None),
            }


@dlt.resource(
    name="comments",
    write_disposition="merge",
    primary_key=list(Comment.__pk__),
    columns=dataclass_to_dlt_columns(Comment),
)
def comments(client: Any, detailed: list[Any]) -> Iterator[dict[str, Any]]:
    """For each detailed activity, fetch and yield comments."""
    for d in detailed:
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


@dlt.resource(name="athlete", write_disposition="replace", columns=dataclass_to_dlt_columns(Athlete))
def athlete(client: Any) -> Iterator[dict[str, Any]]:
    """Yield the authenticated Strava athlete profile (single row)."""
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


def _totals(obj: Any, prefix: str) -> dict[str, Any]:
    return {
        f"{prefix}_count": int(getattr(obj, "count", 0) or 0),
        f"{prefix}_distance_m": _q(getattr(obj, "distance", None)) or 0.0,
        f"{prefix}_moving_time_s": _i(getattr(obj, "moving_time", None)) or 0,
    }


@dlt.resource(name="athlete_stats", write_disposition="replace", columns=dataclass_to_dlt_columns(AthleteStats))
def athlete_stats(client: Any) -> Iterator[dict[str, Any]]:
    """Yield aggregated athlete totals (single row)."""
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
        row.update(_totals(getattr(stats, field, None), prefix))
    yield row


def _zone_list(zone_obj: Any) -> str | None:
    """Serialize a stravalib zones object to JSON list of {min, max}."""
    if zone_obj is None:
        return None
    zones = getattr(zone_obj, "zones", None)
    if not zones:
        return None
    return json.dumps([{"min": getattr(z, "min", None), "max": getattr(z, "max", None)} for z in zones])


@dlt.resource(name="athlete_zones", write_disposition="replace", columns=dataclass_to_dlt_columns(AthleteZones))
def athlete_zones(client: Any) -> Iterator[dict[str, Any]]:
    """Yield athlete heart rate + power zones as JSON blobs (single row)."""
    me = client.get_athlete()
    try:
        zones = client.get_athlete_zones()
    except Exception:
        return
    yield {
        "athlete_id": int(me.id),
        "heart_rate_zones": _zone_list(getattr(zones, "heart_rate", None)),
        "power_zones": _zone_list(getattr(zones, "power", None)),
    }


@dlt.resource(
    name="gear",
    write_disposition="merge",
    primary_key=list(Gear.__pk__),
    columns=dataclass_to_dlt_columns(Gear),
)
def gear(client: Any) -> Iterator[dict[str, Any]]:
    """Yield bikes and shoes with cumulative distance."""
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
                "name": getattr(detail, "name", None) or getattr(item, "name", None),
                "brand_name": getattr(detail, "brand_name", None),
                "model_name": getattr(detail, "model_name", None),
                "distance_m": _q(getattr(detail, "distance", None)) or _q(getattr(item, "distance", None)),
                "primary": bool(getattr(detail, "primary", False) or getattr(item, "primary", False)),
                "retired": bool(getattr(detail, "retired", False) or getattr(item, "retired", False)),
            }
