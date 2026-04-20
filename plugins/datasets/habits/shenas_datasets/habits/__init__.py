from typing import ClassVar

from app.table import Field
from shenas_datasets.core import Dataset
from shenas_datasets.habits.metrics import ALL_TABLES, DailyHabits


class HabitsSchema(Dataset):
    name = "habits"
    display_name = "Habits"
    description = "Daily habit tracking: boolean per-habit columns"
    all_tables = ALL_TABLES
    primary_table = "daily_habits"
    entity_types: ClassVar[list[str]] = ["human"]


__all__ = [
    "ALL_TABLES",
    "DailyHabits",
    "Field",
    "HabitsSchema",
]
