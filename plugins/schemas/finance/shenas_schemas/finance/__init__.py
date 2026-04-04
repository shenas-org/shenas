from shenas_schemas.core import Field, MetricProvider, Schema, generate_ddl, table_metadata
from shenas_schemas.finance.metrics import (
    ALL_TABLES,
    DailySpending,
    MonthlyCategory,
    MonthlyOverview,
    Transaction,
)


class FinanceSchema(Schema):
    name = "finance"
    display_name = "Finance Metrics"
    description = "Canonical finance metrics: transactions, spending, budgets"
    all_tables = ALL_TABLES


__all__ = [
    "ALL_TABLES",
    "DailySpending",
    "Field",
    "FinanceSchema",
    "MetricProvider",
    "MonthlyCategory",
    "MonthlyOverview",
    "Transaction",
    "generate_ddl",
    "table_metadata",
]
