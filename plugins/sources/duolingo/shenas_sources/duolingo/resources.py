"""Duolingo dlt resources -- daily XP, courses, streak."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.duolingo.tables import Course, DailyXP, UserProfile

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.duolingo.client import DuolingoClient


def _epoch_to_date(epoch: int) -> date:
    """Convert epoch seconds to a date object."""
    return datetime.fromtimestamp(epoch, tz=UTC).date()


@dlt.resource(
    write_disposition="merge",
    primary_key=list(DailyXP.__pk__),
    columns=dataclass_to_dlt_columns(DailyXP),
)
def daily_xp(
    client: DuolingoClient,
    start_date: str,
    cursor: dlt.sources.incremental[date] = dlt.sources.incremental("date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield daily XP summaries."""
    effective_start = str(cursor.last_value or start_date)[:10]
    for summary in client.get_xp_summaries(effective_start):
        raw_date = summary.get("date")
        if raw_date is None:
            continue
        d = _epoch_to_date(raw_date) if isinstance(raw_date, int) else date.fromisoformat(str(raw_date)[:10])
        yield {
            "date": d,
            "xp_gained": summary.get("gainedXp") or 0,
            "num_sessions": summary.get("numSessions") or 0,
            "total_session_time_sec": summary.get("totalSessionTime") or 0,
        }


@dlt.resource(
    write_disposition="replace",
    columns=dataclass_to_dlt_columns(Course),
)
def courses(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the user's active language courses."""
    yield from client.get_courses()


@dlt.resource(
    write_disposition="replace",
    columns=dataclass_to_dlt_columns(UserProfile),
)
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
