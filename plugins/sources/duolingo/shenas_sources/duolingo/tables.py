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
    """User profile and streak info."""

    __table__: ClassVar[str] = "user_profile"
    __pk__: ClassVar[tuple[str, ...]] = ("username",)
    __kind__: ClassVar[TableKind] = "snapshot"

    username: Annotated[str, Field(db_type="VARCHAR", description="Duolingo username")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    streak: Annotated[int | None, Field(db_type="INTEGER", description="Current streak in days")] = None
    total_xp: Annotated[int | None, Field(db_type="INTEGER", description="Lifetime XP")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Account creation date")] = None
    current_course: Annotated[str | None, Field(db_type="VARCHAR", description="Active learning language")] = None
    from_language: Annotated[str | None, Field(db_type="VARCHAR", description="Interface language")] = None
