from app.table import Field
from shenas_datasets.core import Dataset
from shenas_datasets.finance.metrics import (
    ALL_TABLES,
    DailySpending,
    MonthlyCategory,
    MonthlyOverview,
    Transaction,
)


class FinanceSchema(Dataset):
    name = "finance"
    display_name = "Finance Metrics"
    description = "Canonical finance metrics: transactions, spending, budgets"
    all_tables = ALL_TABLES
    primary_table = "transactions"


__all__ = [
    "ALL_TABLES",
    "DailySpending",
    "Field",
    "FinanceSchema",
    "MonthlyCategory",
    "MonthlyOverview",
    "Transaction",
]
