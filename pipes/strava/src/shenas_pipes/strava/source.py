"""Strava dlt resources -- activities, athlete profile, stats."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
import pendulum

from shenas_pipes.strava.client import StravaClient


@dlt.resource(write_disposition="merge", primary_key="id")
def activities(
    client: StravaClient,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("start_date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield activities with pagination, using 'after' for incremental sync."""
    effective_start = cursor.last_value or start_date
    after_epoch = int(pendulum.parse(effective_start[:10]).timestamp())

    page = 1
    while True:
        batch = client.get_activities(after=after_epoch, page=page)
        if not batch:
            break
        for act in batch:
            yield {
                "id": act["id"],
                "name": act.get("name", ""),
                "type": act.get("type", ""),
                "sport_type": act.get("sport_type", ""),
                "start_date": act.get("start_date", ""),
                "start_date_local": act.get("start_date_local", ""),
                "timezone": act.get("timezone", ""),
                "distance_m": act.get("distance", 0),
                "moving_time_sec": act.get("moving_time", 0),
                "elapsed_time_sec": act.get("elapsed_time", 0),
                "total_elevation_gain_m": act.get("total_elevation_gain", 0),
                "average_speed_mps": act.get("average_speed", 0),
                "max_speed_mps": act.get("max_speed", 0),
                "average_heartrate": act.get("average_heartrate"),
                "max_heartrate": act.get("max_heartrate"),
                "average_cadence": act.get("average_cadence"),
                "average_watts": act.get("average_watts"),
                "calories": act.get("calories", 0),
                "has_heartrate": act.get("has_heartrate", False),
                "suffer_score": act.get("suffer_score"),
                "trainer": act.get("trainer", False),
                "commute": act.get("commute", False),
                "manual": act.get("manual", False),
                "gear_id": act.get("gear_id"),
                "device_name": act.get("device_name"),
            }
        if len(batch) < 200:
            break
        page += 1


@dlt.resource(write_disposition="replace")
def athlete(client: StravaClient) -> Iterator[dict[str, Any]]:
    """Yield the authenticated athlete's profile."""
    data = client.get_athlete()
    yield {
        "id": data["id"],
        "username": data.get("username", ""),
        "firstname": data.get("firstname", ""),
        "lastname": data.get("lastname", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "country": data.get("country", ""),
        "sex": data.get("sex", ""),
        "weight": data.get("weight"),
        "created_at": data.get("created_at", ""),
    }


@dlt.resource(write_disposition="replace")
def athlete_stats(client: StravaClient) -> Iterator[dict[str, Any]]:
    """Yield aggregated athlete stats (YTD, all-time, recent)."""
    profile = client.get_athlete()
    data = client.get_athlete_stats(profile["id"])
    for period in (
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
        totals = data.get(period)
        if not totals:
            continue
        parts = period.split("_", 1)
        yield {
            "period": parts[0],
            "sport": parts[1].replace("_totals", ""),
            "count": totals.get("count", 0),
            "distance_m": totals.get("distance", 0),
            "moving_time_sec": totals.get("moving_time", 0),
            "elapsed_time_sec": totals.get("elapsed_time", 0),
            "elevation_gain_m": totals.get("elevation_gain", 0),
            "achievement_count": totals.get("achievement_count", 0),
        }
