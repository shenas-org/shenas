from typing import ClassVar

from app.table import Field
from shenas_datasets.core import Dataset
from shenas_datasets.outcomes.metrics import ALL_TABLES, DailyOutcome


class OutcomesSchema(Dataset):
    name = "outcomes"
    display_name = "Outcomes"
    description = "Daily self-reported outcomes: mood, stress, productivity, health"
    all_tables = ALL_TABLES
    primary_table = "daily_outcomes"
    entity_types: ClassVar[list[str]] = ["human"]


__all__ = [
    "ALL_TABLES",
    "DailyOutcome",
    "Field",
    "OutcomesSchema",
]
