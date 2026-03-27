from shenas_schemas.finance.ddl import CANONICAL_TABLES, ensure_schema, generate_ddl
from shenas_schemas.finance.field import Field
from shenas_schemas.finance.introspect import schema_metadata, table_metadata
from shenas_schemas.finance.metrics import (
    ALL_TABLES,
    DailySpending,
    MonthlyCategory,
    MonthlyOverview,
    Transaction,
)
from shenas_schemas.finance.provider import MetricProvider

try:
    from importlib.metadata import version

    _version = version("shenas-schema-finance")
except Exception:
    _version = "dev"

SCHEMA = {
    "name": "finance",
    "version": _version,
    "tables": CANONICAL_TABLES,
}

__all__ = [
    "ALL_TABLES",
    "CANONICAL_TABLES",
    "DailySpending",
    "Field",
    "MetricProvider",
    "MonthlyCategory",
    "MonthlyOverview",
    "SCHEMA",
    "Transaction",
    "ensure_schema",
    "generate_ddl",
    "schema_metadata",
    "table_metadata",
]
