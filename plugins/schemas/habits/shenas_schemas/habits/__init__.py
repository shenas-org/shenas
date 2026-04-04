from shenas_pipes.core.abc import Schema
from shenas_schemas.core import Field, MetricProvider, generate_ddl, table_metadata
from shenas_schemas.habits.metrics import ALL_TABLES, DailyHabits


class HabitsSchema(Schema):
    name = "habits"
    display_name = "Daily Habits"
    description = "Daily habit tracking: boolean per-habit columns"
    all_tables = ALL_TABLES


__all__ = [
    "ALL_TABLES",
    "DailyHabits",
    "Field",
    "HabitsSchema",
    "MetricProvider",
    "generate_ddl",
    "table_metadata",
]
