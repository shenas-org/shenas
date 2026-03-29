"""Duolingo dlt resources -- daily XP, courses, streak."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt

from shenas_pipes.duolingo.client import DuolingoClient


@dlt.resource(write_disposition="merge", primary_key="date")
def daily_xp(
    client: DuolingoClient,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield daily XP summaries."""
    effective_start = (cursor.last_value or start_date)[:10]
    for summary in client.get_xp_summaries(effective_start):
        date = summary.get("date")
        if not date:
            continue
        yield {
            "date": date,
            "xp_gained": summary.get("gainedXp", 0),
            "num_sessions": summary.get("numSessions", 0),
            "total_session_time_sec": summary.get("totalSessionTime", 0),
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
        "user_id": data.get("id"),
        "username": data.get("username", ""),
        "name": data.get("name", ""),
        "streak": data.get("streak_extended_today", data.get("site_streak", 0)),
        "longest_streak": data.get("longest_streak", 0),
        "total_xp": data.get("totalXp", 0),
        "created_at": data.get("creationDate"),
        "current_course": data.get("learningLanguage", ""),
        "from_language": data.get("fromLanguage", ""),
    }
