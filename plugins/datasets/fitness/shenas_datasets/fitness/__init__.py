from typing import ClassVar

from app.table import Field
from shenas_datasets.core import Dataset
from shenas_datasets.fitness.metrics import ALL_TABLES, DailyBody, DailyHRV, DailySleep, DailyVitals


class FitnessSchema(Dataset):
    name = "fitness"
    display_name = "Fitness"
    description = "Canonical fitness metrics: HRV, sleep, vitals, body composition"
    all_tables = ALL_TABLES
    primary_table = "daily_hrv"
    entity_types: ClassVar[list[str]] = ["human"]
    default_update_frequency = "R/P1D"


__all__ = [
    "ALL_TABLES",
    "DailyBody",
    "DailyHRV",
    "DailySleep",
    "DailyVitals",
    "Field",
    "FitnessSchema",
]
