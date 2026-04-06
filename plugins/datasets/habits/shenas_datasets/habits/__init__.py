from shenas_datasets.core import Dataset, MetricProvider
from shenas_datasets.habits.metrics import ALL_TABLES, DailyHabits
from shenas_plugins.core import Field, generate_ddl, table_metadata


class HabitsSchema(Dataset):
    name = "habits"
    display_name = "Daily Habits"
    description = "Daily habit tracking: boolean per-habit columns"
    all_tables = ALL_TABLES
    primary_table = "daily_habits"


__all__ = [
    "ALL_TABLES",
    "DailyHabits",
    "Field",
    "HabitsSchema",
    "MetricProvider",
    "generate_ddl",
    "table_metadata",
]
