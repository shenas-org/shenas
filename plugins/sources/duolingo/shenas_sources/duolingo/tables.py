"""Duolingo source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Notable design choices:

- ``DailyXp`` is an ``AggregateTable`` keyed on ``date`` (the window key).
- ``Achievements`` is an ``EventTable`` keyed on (achievement_name, tier);
  ``time_at`` is ``unlocked_at``.
- ``League`` is an ``AggregateTable`` keyed on ``cohort_id`` (a week is
  the window).
- ``Courses``, ``UserProfile``, ``Friends`` are ``SnapshotTable`` (SCD2).
  Friends in particular benefits: when the user unfollows someone, the
  link row's ``_dlt_valid_to`` is closed instead of leaving it alive
  forever (the previous "replace" loader silently lost history).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import (
    AggregateTable,
    EventTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.duolingo.client import DuolingoClient


def _epoch_to_iso(epoch: int | None) -> str | None:
    """Convert epoch seconds to UTC ISO string. Used by Achievements and League."""
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class DailyXp(AggregateTable):
    """Daily XP summary -- one row per day."""

    class _Meta:
        name = "daily_xp"
        display_name = "Daily XP"
        description = "Daily XP totals from Duolingo's xp_summaries endpoint."
        pk = ("date",)
        time_at = "date"
        plot = (PlotHint("xp_gained"), PlotHint("num_sessions"), PlotHint("total_session_time_sec"))

    cursor_column: ClassVar[str] = "date"

    date: Annotated[date | None, Field(db_type="DATE", description="Day of activity", display_name="Date")] = None
    xp_gained: Annotated[int, Field(db_type="INTEGER", description="XP earned", display_name="XP Gained")] = 0
    num_sessions: Annotated[
        int, Field(db_type="INTEGER", description="Number of practice sessions", display_name="Sessions")
    ] = 0
    total_session_time_sec: Annotated[
        int, Field(db_type="INTEGER", description="Total session time in seconds", display_name="Session Time", unit="s")
    ] = 0

    @staticmethod
    def _epoch_to_date(epoch: int) -> date:
        return datetime.fromtimestamp(epoch, tz=UTC).date()  # ty: ignore[invalid-return-type]

    @classmethod
    def extract(
        cls,
        client: DuolingoClient,
        *,
        start_date: str = "30 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        effective_start = str((cursor.last_value if cursor is not None else None) or start_date)[:10]
        for summary in client.get_xp_summaries(effective_start):
            raw_date = summary.get("date")
            if raw_date is None:
                continue
            d = cls._epoch_to_date(raw_date) if isinstance(raw_date, int) else date.fromisoformat(str(raw_date)[:10])
            yield {
                "date": d,
                "xp_gained": summary.get("gainedXp") or 0,
                "num_sessions": summary.get("numSessions") or 0,
                "total_session_time_sec": summary.get("totalSessionTime") or 0,
            }


class Courses(SnapshotTable):
    """Active language course. SCD2 captures progress changes."""

    class _Meta:
        name = "courses"
        display_name = "Courses"
        description = "Active language courses."
        pk = ("id",)
        plot = (PlotHint("xp", group_by="learning_language", chart_type="bar"),)

    id: Annotated[str, Field(db_type="VARCHAR", description="Course ID", display_name="Course ID")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Course title", display_name="Title")] = None
    from_language: Annotated[
        str | None, Field(db_type="VARCHAR", description="Source language", display_name="From Language")
    ] = None
    learning_language: Annotated[
        str | None, Field(db_type="VARCHAR", description="Target language", display_name="Learning Language")
    ] = None
    xp: Annotated[int | None, Field(db_type="INTEGER", description="Total XP in course", display_name="XP")] = None
    crowns: Annotated[int | None, Field(db_type="INTEGER", description="Crowns earned", display_name="Crowns")] = None

    @classmethod
    def extract(cls, client: DuolingoClient, **_: Any) -> Iterator[dict[str, Any]]:
        yield from client.get_courses()


class UserProfile(SnapshotTable):
    """User profile, streak details, daily goal, and subscription state."""

    class _Meta:
        name = "user_profile"
        display_name = "User Profile"
        description = "Authenticated Duolingo user profile."
        pk = ("username",)

    username: Annotated[str, Field(db_type="VARCHAR", description="Duolingo username", display_name="Username")]
    display_name_: Annotated[str | None, Field(db_type="VARCHAR", description="Display name", display_name="Display Name")] = (
        None
    )
    streak: Annotated[int | None, Field(db_type="INTEGER", description="Current streak in days", display_name="Streak")] = None
    longest_streak: Annotated[
        int | None, Field(db_type="INTEGER", description="Longest streak ever (days)", display_name="Longest Streak")
    ] = None
    streak_start: Annotated[
        str | None, Field(db_type="DATE", description="Current streak start date", display_name="Streak Start")
    ] = None
    streak_freezes_used: Annotated[
        int | None, Field(db_type="INTEGER", description="Streak freezes used", display_name="Freezes Used")
    ] = None
    daily_goal_xp: Annotated[
        int | None, Field(db_type="INTEGER", description="Daily XP goal", display_name="Daily XP Goal")
    ] = None
    total_xp: Annotated[int | None, Field(db_type="INTEGER", description="Lifetime XP", display_name="Total XP")] = None
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Account creation date", display_name="Created At")
    ] = None
    current_course: Annotated[
        str | None, Field(db_type="VARCHAR", description="Active learning language", display_name="Current Course")
    ] = None
    from_language: Annotated[
        str | None, Field(db_type="VARCHAR", description="Interface language", display_name="From Language")
    ] = None
    has_super: Annotated[
        bool, Field(db_type="BOOLEAN", description="Has Super Duolingo subscription", display_name="Has Super")
    ] = False
    following_count: Annotated[
        int | None, Field(db_type="INTEGER", description="Accounts followed", display_name="Following")
    ] = None
    followers_count: Annotated[int | None, Field(db_type="INTEGER", description="Followers", display_name="Followers")] = None

    @classmethod
    def extract(cls, client: DuolingoClient, **_: Any) -> Iterator[dict[str, Any]]:
        data = client.get_user()
        streak_data = data.get("streakData") or {}
        current_streak = streak_data.get("currentStreak") or {}
        longest_streak = streak_data.get("longestStreak") or {}
        following = client.get_following()
        followers = client.get_followers()
        yield {
            "username": data.get("username", ""),
            "display_name_": data.get("name"),
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


class Achievements(EventTable):
    """An achievement / badge unlocked by the user."""

    class _Meta:
        name = "achievements"
        display_name = "Achievements"
        description = "Unlocked Duolingo achievements / badges."
        pk = ("achievement_name", "tier")
        time_at = "unlocked_at"

    achievement_name: Annotated[str, Field(db_type="VARCHAR", description="Achievement key", display_name="Achievement")]
    tier: Annotated[int, Field(db_type="INTEGER", description="Tier (0-based)", display_name="Tier")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Display title", display_name="Title")] = None
    achievement_description: Annotated[
        str | None, Field(db_type="VARCHAR", description="Description", display_name="Description")
    ] = None
    count: Annotated[int | None, Field(db_type="INTEGER", description="Counter value", display_name="Count")] = None
    unlocked_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Unlocked timestamp (UTC)", display_name="Unlocked At")
    ] = None

    @classmethod
    def extract(cls, client: DuolingoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for a in client.get_achievements():
            yield {
                "achievement_name": a.get("name") or a.get("achievementName") or "",
                "tier": int(a.get("tier") or a.get("currentTier") or 0),
                "title": a.get("title") or a.get("displayTitle"),
                "achievement_description": a.get("description") or a.get("displayDescription"),
                "count": a.get("count"),
                "unlocked_at": _epoch_to_iso(a.get("unlockTimestamp") or a.get("unlockedAt")),
            }


class League(AggregateTable):
    """Weekly league standing for the user."""

    class _Meta:
        name = "league"
        display_name = "League"
        description = "Weekly league standings (cohort = week)."
        pk = ("cohort_id",)
        time_at = "cohort_end"
        plot = (PlotHint("weekly_xp"), PlotHint("rank"))

    cohort_id: Annotated[str, Field(db_type="VARCHAR", description="Cohort ID for this week", display_name="Cohort ID")]
    league_tier: Annotated[
        int | None, Field(db_type="INTEGER", description="League tier (0=Bronze ... 9=Diamond)", display_name="League Tier")
    ] = None
    league_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Human-readable league name", display_name="League Name")
    ] = None
    rank: Annotated[int | None, Field(db_type="INTEGER", description="User's rank in cohort", display_name="Rank")] = None
    weekly_xp: Annotated[int | None, Field(db_type="INTEGER", description="XP earned this week", display_name="Weekly XP")] = (
        None
    )
    cohort_size: Annotated[
        int | None, Field(db_type="INTEGER", description="Number of users in cohort", display_name="Cohort Size")
    ] = None
    cohort_end: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Cohort end time (UTC)", display_name="Cohort End")
    ] = None

    LEAGUE_NAMES: ClassVar[tuple[str, ...]] = (
        "Bronze",
        "Silver",
        "Gold",
        "Sapphire",
        "Ruby",
        "Emerald",
        "Amethyst",
        "Pearl",
        "Obsidian",
        "Diamond",
    )

    @classmethod
    def extract(cls, client: DuolingoClient, **_: Any) -> Iterator[dict[str, Any]]:
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
            "league_name": (cls.LEAGUE_NAMES[tier] if isinstance(tier, int) and 0 <= tier < len(cls.LEAGUE_NAMES) else None),
            "rank": rank,
            "weekly_xp": weekly_xp,
            "cohort_size": len(users) or None,
            "cohort_end": _epoch_to_iso(cohort.get("cohortEndDate")),
        }


class Friends(SnapshotTable):
    """Users this user follows. SCD2 closes a row when unfollowed."""

    class _Meta:
        name = "friends"
        display_name = "Friends"
        description = "Users this user follows; flagged is_follower if mutual."
        pk = ("user_id",)

    user_id: Annotated[int, Field(db_type="BIGINT", description="Friend's user ID", display_name="User ID")]
    username: Annotated[str | None, Field(db_type="VARCHAR", description="Friend's username", display_name="Username")] = None
    display_name_: Annotated[
        str | None, Field(db_type="VARCHAR", description="Friend's display name", display_name="Display Name")
    ] = None
    total_xp: Annotated[int | None, Field(db_type="INTEGER", description="Friend's lifetime XP", display_name="Total XP")] = (
        None
    )
    streak: Annotated[int | None, Field(db_type="INTEGER", description="Friend's current streak", display_name="Streak")] = (
        None
    )
    has_subscription: Annotated[bool, Field(db_type="BOOLEAN", description="Friend has Super", display_name="Has Super")] = (
        False
    )
    is_follower: Annotated[
        bool, Field(db_type="BOOLEAN", description="Friend also follows back", display_name="Follows Back")
    ] = False

    @classmethod
    def extract(cls, client: DuolingoClient, **_: Any) -> Iterator[dict[str, Any]]:
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
                "display_name_": u.get("displayName") or u.get("name"),
                "total_xp": u.get("totalXp"),
                "streak": u.get("streak"),
                "has_subscription": bool(u.get("hasSubscription") or u.get("hasPlus")),
                "is_follower": int(uid) in follower_ids,
            }


TABLES: tuple[type[SourceTable], ...] = (DailyXp, Courses, UserProfile, Achievements, League, Friends)
