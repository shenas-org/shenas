from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier")]


@dataclass
class DailyHabits:
    """Daily habit tracking -- one row per (date, source)."""

    __table__: ClassVar[str] = "daily_habits"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: Source
    duolingo: (
        Annotated[
            bool,
            Field(
                db_type="BOOLEAN",
                description="Completed at least one Duolingo lesson today",
                category="growth",
                interpretation="True if any XP was earned; track streaks and consistency over time",
            ),
        ]
        | None
    ) = None


ALL_TABLES = [DailyHabits]
