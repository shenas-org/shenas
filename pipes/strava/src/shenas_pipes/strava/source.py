"""Strava dlt resources -- activities, athlete profile, stats."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
from stravalib import Client


def _quantity_val(v: Any) -> Any:
    """Extract raw number from a stravalib Pint Quantity, or return as-is."""
    if hasattr(v, "magnitude"):
        return v.magnitude
    return v


@dlt.resource(write_disposition="merge", primary_key="id")
def activities(
    client: Client,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("start_date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield activities using stravalib's paginated iterator."""
    effective_start = cursor.last_value or start_date
    after_dt = effective_start[:10]  # stravalib accepts ISO date strings

    for act in client.get_activities(after=after_dt):
        yield {
            "id": act.id,
            "name": act.name or "",
            "type": str(act.type) if act.type else "",
            "sport_type": str(act.sport_type) if act.sport_type else "",
            "start_date": act.start_date.isoformat() if act.start_date else "",
            "start_date_local": act.start_date_local.isoformat() if act.start_date_local else "",
            "timezone": str(act.timezone) if act.timezone else "",
            "distance_m": _quantity_val(act.distance) or 0,
            "moving_time_sec": _quantity_val(act.moving_time) or 0,
            "elapsed_time_sec": _quantity_val(act.elapsed_time) or 0,
            "total_elevation_gain_m": _quantity_val(act.total_elevation_gain) or 0,
            "average_speed_mps": _quantity_val(act.average_speed) or 0,
            "max_speed_mps": _quantity_val(act.max_speed) or 0,
            "average_heartrate": act.average_heartrate,
            "max_heartrate": act.max_heartrate,
            "average_cadence": act.average_cadence,
            "average_watts": act.average_watts,
            "kilojoules": _quantity_val(act.kilojoules) or 0,
            "has_heartrate": act.has_heartrate or False,
            "suffer_score": act.suffer_score,
            "trainer": act.trainer or False,
            "commute": act.commute or False,
            "manual": act.manual or False,
            "gear_id": act.gear_id,
        }


@dlt.resource(write_disposition="replace")
def athlete(client: Client) -> Iterator[dict[str, Any]]:
    """Yield the authenticated athlete's profile."""
    data = client.get_athlete()
    yield {
        "id": data.id,
        "username": data.username or "",
        "firstname": data.firstname or "",
        "lastname": data.lastname or "",
        "city": data.city or "",
        "state": data.state or "",
        "country": data.country or "",
        "sex": data.sex or "",
        "weight": _quantity_val(data.weight),
        "created_at": data.created_at.isoformat() if data.created_at else "",
    }


@dlt.resource(write_disposition="replace")
def athlete_stats(client: Client) -> Iterator[dict[str, Any]]:
    """Yield aggregated athlete stats (YTD, all-time, recent)."""
    profile = client.get_athlete()
    data = client.get_athlete_stats(profile.id)
    for period_name in (
        "recent_run_totals",
        "recent_ride_totals",
        "recent_swim_totals",
        "ytd_run_totals",
        "ytd_ride_totals",
        "ytd_swim_totals",
        "all_run_totals",
        "all_ride_totals",
        "all_swim_totals",
    ):
        totals = getattr(data, period_name, None)
        if not totals:
            continue
        parts = period_name.split("_", 1)
        yield {
            "period": parts[0],
            "sport": parts[1].replace("_totals", ""),
            "count": totals.count or 0,
            "distance_m": _quantity_val(totals.distance) or 0,
            "moving_time_sec": _quantity_val(totals.moving_time) or 0,
            "elapsed_time_sec": _quantity_val(totals.elapsed_time) or 0,
            "elevation_gain_m": _quantity_val(totals.elevation_gain) or 0,
            "achievement_count": totals.achievement_count or 0,
        }
