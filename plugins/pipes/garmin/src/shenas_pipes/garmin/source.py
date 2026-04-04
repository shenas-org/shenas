from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dlt
import pendulum

from shenas_pipes.core.utils import date_range, is_empty_response

if TYPE_CHECKING:
    from collections.abc import Iterator

    from garminconnect import Garmin


@dlt.resource(write_disposition="merge", primary_key="activity_id")
def activities(
    client: Garmin,
    start_date: str,
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental("startTimeLocal", initial_value=None),
) -> Iterator[dict[str, Any]]:
    effective_start = (updated_at.last_value or start_date)[:10]
    end_date = pendulum.now().to_date_string()
    rows = client.get_activities_by_date(effective_start, end_date) or []
    for row in rows:
        row["activity_id"] = str(row["activityId"])
        yield row


@dlt.resource(write_disposition="merge", primary_key="calendarDate")
def daily_stats(
    client: Garmin,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("calendarDate", initial_value=None),
) -> Iterator[dict[str, Any]]:
    for date in date_range(cursor.last_value or start_date):
        data = client.get_user_summary(date)
        if is_empty_response(data, sentinel_key="totalSteps"):
            continue
        yield data


@dlt.resource(write_disposition="merge", primary_key="calendarDate")
def sleep(
    client: Garmin,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("calendarDate", initial_value=None),
) -> Iterator[dict[str, Any]]:
    for date in date_range(cursor.last_value or start_date):
        data = client.get_sleep_data(date)
        if not data:
            continue
        data["calendarDate"] = date
        yield data


@dlt.resource(write_disposition="merge", primary_key="calendarDate")
def hrv(
    client: Garmin,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("calendarDate", initial_value=None),
) -> Iterator[dict[str, Any]]:
    for date in date_range(cursor.last_value or start_date):
        data = client.get_hrv_data(date)
        if not data:
            continue
        data["calendarDate"] = date
        yield data


@dlt.resource(write_disposition="merge", primary_key="calendarDate")
def spo2(
    client: Garmin,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("calendarDate", initial_value=None),
) -> Iterator[dict[str, Any]]:
    for date in date_range(cursor.last_value or start_date):
        data = client.get_spo2_data(date)
        if is_empty_response(data):
            continue
        yield data


@dlt.resource(write_disposition="merge", primary_key="samplePk")
def body_composition(client: Garmin, start_date: str) -> Iterator[dict[str, Any]]:
    end_date = pendulum.now().to_date_string()
    data = client.get_body_composition(start_date, end_date)
    if not data:
        return
    entries = data.get("dateWeightList") or data.get("totalAverage") or []
    if isinstance(entries, dict):
        entries = [entries]
    yield from entries
