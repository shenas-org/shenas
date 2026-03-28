from shenas_schemas.fitness_tracker.ddl import CANONICAL_TABLES, ensure_schema, generate_ddl
from shenas_schemas.fitness_tracker.field import Field
from shenas_schemas.fitness_tracker.introspect import schema_metadata, table_metadata
from shenas_schemas.fitness_tracker.metrics import ALL_TABLES, DailyBody, DailyHRV, DailySleep, DailyVitals
from shenas_schemas.fitness_tracker.provider import MetricProvider

try:
    from importlib.metadata import version

    _version = version("shenas-schema-fitness-tracker")
except Exception:
    _version = "dev"

SCHEMA = {
    "name": "fitness-tracker",
    "version": _version,
    "tables": CANONICAL_TABLES,
}

__all__ = [
    "ALL_TABLES",
    "CANONICAL_TABLES",
    "DailyBody",
    "DailyHRV",
    "DailySleep",
    "DailyVitals",
    "Field",
    "MetricProvider",
    "SCHEMA",
    "ensure_schema",
    "generate_ddl",
    "schema_metadata",
    "table_metadata",
]
