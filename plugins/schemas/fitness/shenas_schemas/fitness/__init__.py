from shenas_schemas.core import Field, MetricProvider, Schema, generate_ddl, table_metadata
from shenas_schemas.fitness.metrics import ALL_TABLES, DailyBody, DailyHRV, DailySleep, DailyVitals


class FitnessSchema(Schema):
    name = "fitness"
    display_name = "Fitness Metrics"
    description = "Canonical fitness metrics: HRV, sleep, vitals, body composition"
    all_tables = ALL_TABLES


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
