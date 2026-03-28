from functools import partial

from shenas_schemas.core import Field, MetricProvider, generate_ddl, table_metadata
from shenas_schemas.core.ddl import ensure_schema as _ensure_schema
from shenas_schemas.core.introspect import schema_metadata as _schema_metadata
from shenas_schemas.fitness.metrics import ALL_TABLES, DailyBody, DailyHRV, DailySleep, DailyVitals

CANONICAL_TABLES = [cls.__table__ for cls in ALL_TABLES]

ensure_schema = partial(_ensure_schema, all_tables=ALL_TABLES)
schema_metadata = partial(_schema_metadata, all_tables=ALL_TABLES)

try:
    from importlib.metadata import version

    _version = version("shenas-schema-fitness")
except Exception:
    _version = "dev"

SCHEMA = {
    "name": "fitness",
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
