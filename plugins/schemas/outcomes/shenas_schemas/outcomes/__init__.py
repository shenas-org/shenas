from shenas_plugins.core import Schema
from shenas_schemas.core import Field, MetricProvider, generate_ddl, table_metadata
from shenas_schemas.outcomes.metrics import ALL_TABLES, DailyOutcome


class OutcomesSchema(Schema):
    name = "outcomes"
    display_name = "Daily Outcomes"
    description = "Daily self-reported outcomes: mood, stress, productivity, health"
    all_tables = ALL_TABLES


__all__ = [
    "ALL_TABLES",
    "DailyOutcome",
    "Field",
    "MetricProvider",
    "OutcomesSchema",
    "generate_ddl",
    "table_metadata",
]
