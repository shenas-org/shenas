"""Duolingo dlt resources -- daily XP, courses, streak."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import dlt

from shenas_pipes.duolingo.client import DuolingoClient


def _epoch_to_date(epoch: int) -> str:
    """Convert epoch seconds to ISO date string."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")


@dlt.resource(write_disposition="merge", primary_key="date")
def daily_xp(
    client: DuolingoClient,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield daily XP summaries."""
    effective_start = (cursor.last_value or start_date)[:10]
    for summary in client.get_xp_summaries(effective_start):
        raw_date = summary.get("date")
        if raw_date is None:
            continue
        date = _epoch_to_date(raw_date) if isinstance(raw_date, int) else str(raw_date)
        yield {
            "date": date,
            "xp_gained": summary.get("gainedXp") or 0,
            "num_sessions": summary.get("numSessions") or 0,
            "total_session_time_sec": summary.get("totalSessionTime") or 0,
        }


@dlt.resource(write_disposition="replace")
def courses(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the user's active language courses."""
    yield from client.get_courses()


@dlt.resource(write_disposition="replace")
def user_profile(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the user's profile and streak info."""
    data = client.get_user()
    yield {
        "username": data.get("username", ""),
        "name": data.get("name", ""),
        "streak": data.get("streak", 0),
        "total_xp": data.get("totalXp", 0),
        "created_at": data.get("creationDate"),
        "current_course": data.get("learningLanguage", ""),
        "from_language": data.get("fromLanguage", ""),
    }
