from shenas_datasets.core import Dataset, Field, MetricProvider, generate_ddl, table_metadata
from shenas_datasets.outcomes.metrics import ALL_TABLES, DailyOutcome


class OutcomesSchema(Dataset):
    name = "outcomes"
    display_name = "Daily Outcomes"
    description = "Daily self-reported outcomes: mood, stress, productivity, health"
    all_tables = ALL_TABLES
    primary_table = "daily_outcomes"


__all__ = [
    "ALL_TABLES",
    "DailyOutcome",
    "Field",
    "MetricProvider",
    "OutcomesSchema",
    "generate_ddl",
    "table_metadata",
]
