"""Duolingo dlt resources -- daily XP, courses, profile, achievements, league, friends."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.duolingo.tables import Achievement, Course, DailyXP, Friend, League, UserProfile

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.duolingo.client import DuolingoClient


def _epoch_to_date(epoch: int) -> date:
    """Convert epoch seconds to a date object."""
    return datetime.fromtimestamp(epoch, tz=UTC).date()


def _epoch_to_iso(epoch: int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat()


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
    """Yield the user's profile, streak details, daily goal and subscription state."""
    data = client.get_user()
    streak_data = data.get("streakData") or {}
    current_streak = streak_data.get("currentStreak") or {}
    longest_streak = streak_data.get("longestStreak") or {}
    following = client.get_following()
    followers = client.get_followers()
    yield {
        "username": data.get("username", ""),
        "name": data.get("name"),
        "streak": data.get("streak") or current_streak.get("length"),
        "longest_streak": longest_streak.get("length"),
        "streak_start": current_streak.get("startDate"),
        "streak_freezes_used": streak_data.get("streakFreezesUsed"),
        "daily_goal_xp": data.get("xpGoal"),
        "total_xp": data.get("totalXp", 0),
        "created_at": data.get("creationDate"),
        "current_course": data.get("learningLanguage"),
        "from_language": data.get("fromLanguage"),
        "has_super": bool(data.get("hasPlus") or data.get("subscriberLevel")),
        "following_count": len(following),
        "followers_count": len(followers),
    }


@dlt.resource(
    name="achievements",
    write_disposition="merge",
    primary_key=list(Achievement.__pk__),
    columns=dataclass_to_dlt_columns(Achievement),
)
def achievements(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the user's unlocked achievements."""
    for a in client.get_achievements():
        yield {
            "name": a.get("name") or a.get("achievementName") or "",
            "tier": int(a.get("tier") or a.get("currentTier") or 0),
            "title": a.get("title") or a.get("displayTitle"),
            "description": a.get("description") or a.get("displayDescription"),
            "count": a.get("count"),
            "unlocked_at": _epoch_to_iso(a.get("unlockTimestamp") or a.get("unlockedAt")),
        }


_LEAGUE_NAMES = ["Bronze", "Silver", "Gold", "Sapphire", "Ruby", "Emerald", "Amethyst", "Pearl", "Obsidian", "Diamond"]


@dlt.resource(
    name="league",
    write_disposition="merge",
    primary_key=list(League.__pk__),
    columns=dataclass_to_dlt_columns(League),
)
def league(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the user's current weekly league standing."""
    data = client.get_league()
    if not data:
        return
    cohort = data.get("cohort") or {}
    cohort_id = cohort.get("cohortId") or data.get("cohortId")
    if not cohort_id:
        return
    tier = cohort.get("tier") if cohort.get("tier") is not None else data.get("tier")
    users = cohort.get("rankings") or cohort.get("users") or []
    rank: int | None = None
    weekly_xp: int | None = None
    user_id = client.user_id
    for i, u in enumerate(users):
        if int(u.get("user_id") or u.get("userId") or 0) == user_id:
            rank = i + 1
            weekly_xp = u.get("score") or u.get("totalXp")
            break
    yield {
        "cohort_id": str(cohort_id),
        "league_tier": tier,
        "league_name": _LEAGUE_NAMES[tier] if isinstance(tier, int) and 0 <= tier < len(_LEAGUE_NAMES) else None,
        "rank": rank,
        "weekly_xp": weekly_xp,
        "cohort_size": len(users) or None,
        "cohort_end": _epoch_to_iso(cohort.get("cohortEndDate")),
    }


@dlt.resource(
    name="friends",
    write_disposition="replace",
    columns=dataclass_to_dlt_columns(Friend),
)
def friends(client: DuolingoClient) -> Iterator[dict[str, Any]]:
    """Yield the list of users this user follows.

    A friend is marked is_follower=True if they also follow back.
    """
    following = client.get_following()
    followers = client.get_followers()
    follower_ids = {int(f.get("userId") or f.get("user_id") or 0) for f in followers}
    for u in following:
        uid = u.get("userId") or u.get("user_id")
        if uid is None:
            continue
        yield {
            "user_id": int(uid),
            "username": u.get("username"),
            "display_name": u.get("displayName") or u.get("name"),
            "total_xp": u.get("totalXp"),
            "streak": u.get("streak"),
            "has_subscription": bool(u.get("hasSubscription") or u.get("hasPlus")),
            "is_follower": int(uid) in follower_ids,
        }
