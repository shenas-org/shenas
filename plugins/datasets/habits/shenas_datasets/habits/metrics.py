from typing import Annotated, ClassVar

from shenas_datasets.core import DailyMetricTable
from shenas_plugins.core.table import Field

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier")]


class DailyHabits(DailyMetricTable):
    """Daily habit tracking -- one row per (date, source)."""

    table_name: ClassVar[str] = "daily_habits"
    table_display_name: ClassVar[str] = "Daily Habits"
    table_description: ClassVar[str | None] = "Per-day boolean / counter signals from habit-tracking sources."
    table_pk: ClassVar[tuple[str, ...]] = ("date", "source")

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
