from shenas_datasets.core import Dataset
from shenas_datasets.outcomes.metrics import ALL_TABLES, DailyOutcome
from shenas_plugins.core import Field


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
    "OutcomesSchema",
]
