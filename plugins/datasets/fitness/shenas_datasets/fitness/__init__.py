from shenas_datasets.core import Dataset, Field, MetricProvider, generate_ddl, table_metadata
from shenas_datasets.fitness.metrics import ALL_TABLES, DailyBody, DailyHRV, DailySleep, DailyVitals


class FitnessSchema(Dataset):
    name = "fitness"
    display_name = "Fitness Metrics"
    description = "Canonical fitness metrics: HRV, sleep, vitals, body composition"
    all_tables = ALL_TABLES
    primary_table = "daily_hrv"


__all__ = [
    "ALL_TABLES",
    "DailyBody",
    "DailyHRV",
    "DailySleep",
    "DailyVitals",
    "Field",
    "FitnessSchema",
    "MetricProvider",
    "generate_ddl",
    "table_metadata",
]
