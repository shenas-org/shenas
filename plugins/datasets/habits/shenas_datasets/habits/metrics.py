from typing import Annotated

from app.table import Field
from shenas_datasets.core import DailyMetricTable, TransformId

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier", display_name="Source")]


class DailyHabits(DailyMetricTable):
    """Daily habit tracking -- one row per (date, source)."""

    class _Meta:
        name = "daily_habits"
        display_name = "Daily Habits"
        description = "Per-day boolean / counter signals from habit-tracking sources."
        pk = ("date", "transform_id")

    date: Date
    source: Source = ""
    transform_id: TransformId = 0
    duolingo: (
        Annotated[
            bool,
            Field(
                db_type="BOOLEAN",
                description="Completed at least one Duolingo lesson today",
                display_name="Duolingo",
                category="growth",
                interpretation="True if any XP was earned; track streaks and consistency over time",
            ),
        ]
        | None
    ) = None


ALL_TABLES = [DailyHabits]
