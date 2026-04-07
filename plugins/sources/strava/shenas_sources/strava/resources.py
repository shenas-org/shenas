"""Strava dlt resources -- activities, athlete."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.core.utils import resolve_start_date
from shenas_sources.strava.tables import Activity, Athlete

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


def _activity_row(activity: Any) -> dict[str, Any]:
    """Map a stravalib activity object to a flat dict matching Activity."""
    start_date: datetime | None = getattr(activity, "start_date", None)
    return {
        "id": int(activity.id),
        "name": getattr(activity, "name", None),
        "sport_type": str(getattr(activity, "sport_type", "") or "") or None,
        "start_date": start_date.isoformat() if start_date else None,
        "timezone": str(getattr(activity, "timezone", "") or "") or None,
        "distance_m": _q(getattr(activity, "distance", None)),
        "moving_time_s": _i(getattr(activity, "moving_time", None)),
        "elapsed_time_s": _i(getattr(activity, "elapsed_time", None)),
        "elevation_gain_m": _q(getattr(activity, "total_elevation_gain", None)),
        "average_speed_mps": _q(getattr(activity, "average_speed", None)),
        "max_speed_mps": _q(getattr(activity, "max_speed", None)),
        "average_heartrate": _q(getattr(activity, "average_heartrate", None)),
        "max_heartrate": _q(getattr(activity, "max_heartrate", None)),
        "kilojoules": _q(getattr(activity, "kilojoules", None)),
        "calories": _q(getattr(activity, "calories", None)),
        "average_watts": _q(getattr(activity, "average_watts", None)),
        "max_watts": _q(getattr(activity, "max_watts", None)),
        "suffer_score": _q(getattr(activity, "suffer_score", None)),
        "trainer": bool(getattr(activity, "trainer", False)),
        "commute": bool(getattr(activity, "commute", False)),
        "manual": bool(getattr(activity, "manual", False)),
    }


@dlt.resource(
    name="activities",
    write_disposition="merge",
    primary_key=list(Activity.__pk__),
    columns=dataclass_to_dlt_columns(Activity),
)
def activities(client: Any, start_date: str = "30 days ago") -> Iterator[dict[str, Any]]:
    """Yield activities from the authenticated athlete since `start_date`."""
    import pendulum

    after = pendulum.parse(resolve_start_date(start_date))
    for activity in client.get_activities(after=after):
        yield _activity_row(activity)


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
