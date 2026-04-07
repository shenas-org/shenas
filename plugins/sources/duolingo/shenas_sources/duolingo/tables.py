"""Duolingo raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class DailyXP:
    """Daily XP summary -- one row per day."""

    __table__: ClassVar[str] = "daily_xp"
    __pk__: ClassVar[tuple[str, ...]] = ("date",)
    __kind__: ClassVar[TableKind] = "aggregate"

    date: Annotated[str, Field(db_type="DATE", description="Day of activity")]
    xp_gained: Annotated[int, Field(db_type="INTEGER", description="XP earned")] = 0
    num_sessions: Annotated[int, Field(db_type="INTEGER", description="Number of practice sessions")] = 0
    total_session_time_sec: Annotated[int, Field(db_type="INTEGER", description="Total session time in seconds")] = 0


@dataclass
class Course:
    """Active language course."""

    __table__: ClassVar[str] = "courses"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[str, Field(db_type="VARCHAR", description="Course ID")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Course title")] = None
    from_language: Annotated[str | None, Field(db_type="VARCHAR", description="Source language")] = None
    learning_language: Annotated[str | None, Field(db_type="VARCHAR", description="Target language")] = None
    xp: Annotated[int | None, Field(db_type="INTEGER", description="Total XP in course")] = None
    crowns: Annotated[int | None, Field(db_type="INTEGER", description="Crowns earned")] = None


@dataclass
class UserProfile:
    """User profile, streak details, daily goal, and subscription state."""

    __table__: ClassVar[str] = "user_profile"
    __pk__: ClassVar[tuple[str, ...]] = ("username",)
    __kind__: ClassVar[TableKind] = "snapshot"

    username: Annotated[str, Field(db_type="VARCHAR", description="Duolingo username")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    streak: Annotated[int | None, Field(db_type="INTEGER", description="Current streak in days")] = None
    longest_streak: Annotated[int | None, Field(db_type="INTEGER", description="Longest streak ever (days)")] = None
    streak_start: Annotated[str | None, Field(db_type="DATE", description="Current streak start date")] = None
    streak_freezes_used: Annotated[int | None, Field(db_type="INTEGER", description="Streak freezes used")] = None
    daily_goal_xp: Annotated[int | None, Field(db_type="INTEGER", description="Daily XP goal")] = None
    total_xp: Annotated[int | None, Field(db_type="INTEGER", description="Lifetime XP")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Account creation date")] = None
    current_course: Annotated[str | None, Field(db_type="VARCHAR", description="Active learning language")] = None
    from_language: Annotated[str | None, Field(db_type="VARCHAR", description="Interface language")] = None
    has_super: Annotated[bool, Field(db_type="BOOLEAN", description="Has Super Duolingo subscription")] = False
    following_count: Annotated[int | None, Field(db_type="INTEGER", description="Accounts followed")] = None
    followers_count: Annotated[int | None, Field(db_type="INTEGER", description="Followers")] = None


@dataclass
class Achievement:
    """An achievement / badge unlocked by the user."""

    __table__: ClassVar[str] = "achievements"
    __pk__: ClassVar[tuple[str, ...]] = ("name", "tier")
    __kind__: ClassVar[TableKind] = "event"

    name: Annotated[str, Field(db_type="VARCHAR", description="Achievement key")]
    tier: Annotated[int, Field(db_type="INTEGER", description="Tier (0-based)")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Display title")] = None
    description: Annotated[str | None, Field(db_type="VARCHAR", description="Description")] = None
    count: Annotated[int | None, Field(db_type="INTEGER", description="Counter value")] = None
    unlocked_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Unlocked timestamp (UTC)")] = None


@dataclass
class League:
    """Weekly league standing for the user."""

    __table__: ClassVar[str] = "league"
    __pk__: ClassVar[tuple[str, ...]] = ("cohort_id",)
    __kind__: ClassVar[TableKind] = "aggregate"

    cohort_id: Annotated[str, Field(db_type="VARCHAR", description="Cohort ID for this week")]
    league_tier: Annotated[int | None, Field(db_type="INTEGER", description="League tier (0=Bronze ... 9=Diamond)")] = None
    league_name: Annotated[str | None, Field(db_type="VARCHAR", description="Human-readable league name")] = None
    rank: Annotated[int | None, Field(db_type="INTEGER", description="User's rank in cohort")] = None
    weekly_xp: Annotated[int | None, Field(db_type="INTEGER", description="XP earned this week")] = None
    cohort_size: Annotated[int | None, Field(db_type="INTEGER", description="Number of users in cohort")] = None
    cohort_end: Annotated[str | None, Field(db_type="TIMESTAMP", description="Cohort end time (UTC)")] = None


@dataclass
class Friend:
    """A user the authenticated user follows."""

    __table__: ClassVar[str] = "friends"
    __pk__: ClassVar[tuple[str, ...]] = ("user_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    user_id: Annotated[int, Field(db_type="BIGINT", description="Friend's user ID")]
    username: Annotated[str | None, Field(db_type="VARCHAR", description="Friend's username")] = None
    display_name: Annotated[str | None, Field(db_type="VARCHAR", description="Friend's display name")] = None
    total_xp: Annotated[int | None, Field(db_type="INTEGER", description="Friend's lifetime XP")] = None
    streak: Annotated[int | None, Field(db_type="INTEGER", description="Friend's current streak")] = None
    has_subscription: Annotated[bool, Field(db_type="BOOLEAN", description="Friend has Super")] = False
    is_follower: Annotated[bool, Field(db_type="BOOLEAN", description="Friend also follows back")] = False
