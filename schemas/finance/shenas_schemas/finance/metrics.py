from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier (e.g. lunchmoney)")]


@dataclass
class Transaction:
    """Individual financial transaction — one row per (id, source)."""

    __table__: ClassVar[str] = "transactions"
    __pk__: ClassVar[tuple[str, ...]] = ("id", "source")

    id: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Unique transaction identifier from the source system",
        ),
    ]
    source: Source
    date: Date
    amount: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Transaction amount in base currency (negative = expense, positive = income)",
                unit="currency",
                example_value=-42.50,
                category="spending",
                interpretation="Negative values are outflows (expenses); positive values are inflows (income)",
            ),
        ]
        | None
    ) = None
    payee: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Merchant or counterparty name",
                category="spending",
            ),
        ]
        | None
    ) = None
    category: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Spending category (e.g. groceries, rent, entertainment)",
                category="spending",
            ),
        ]
        | None
    ) = None
    category_group: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Parent category group (e.g. food, housing, leisure)",
                category="spending",
            ),
        ]
        | None
    ) = None
    account: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Account name (e.g. checking, credit card, savings)",
                category="account",
            ),
        ]
        | None
    ) = None
    currency: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="ISO 4217 currency code",
                example_value="USD",
            ),
        ]
        | None
    ) = None
    is_income: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Whether this transaction is income (1) or expense (0)",
                value_range=(0, 1),
                category="spending",
            ),
        ]
        | None
    ) = None
    notes: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="User-added notes or memo",
            ),
        ]
        | None
    ) = None
    recurring: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Whether this is a recurring transaction (1) or one-time (0)",
                value_range=(0, 1),
                category="spending",
            ),
        ]
        | None
    ) = None


@dataclass
class DailySpending:
    """Aggregated daily spending — one row per (date, source)."""

    __table__: ClassVar[str] = "daily_spending"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: Source
    total_spent: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total amount spent (sum of expense transactions)",
                unit="currency",
                example_value=85.30,
                category="spending",
                interpretation="Lower daily spending indicates tighter budgeting; track against your daily budget target",
            ),
        ]
        | None
    ) = None
    total_income: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total income received",
                unit="currency",
                example_value=0.0,
                category="income",
                interpretation="Income typically arrives on specific days (payday); most days will be zero",
            ),
        ]
        | None
    ) = None
    transaction_count: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Number of transactions for the day",
                example_value=5,
                category="spending",
                interpretation="Fewer transactions may indicate more intentional spending",
            ),
        ]
        | None
    ) = None


@dataclass
class MonthlyCategory:
    """Monthly spending by category — one row per (month, category, source)."""

    __table__: ClassVar[str] = "monthly_category"
    __pk__: ClassVar[tuple[str, ...]] = ("month", "category", "source")

    month: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Month in YYYY-MM format",
            category="time",
        ),
    ]
    category: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Spending category",
            category="spending",
        ),
    ]
    source: Source
    amount_spent: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total spent in this category for the month",
                unit="currency",
                example_value=320.50,
                category="spending",
                interpretation="Compare month-over-month to detect spending trend changes",
            ),
        ]
        | None
    ) = None
    transaction_count: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Number of transactions in this category",
                example_value=12,
                category="spending",
            ),
        ]
        | None
    ) = None
    budget_amount: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Budget allocated for this category this month",
                unit="currency",
                example_value=400.0,
                category="budget",
                interpretation="When amount_spent exceeds budget_amount, you are over budget for this category",
            ),
        ]
        | None
    ) = None


@dataclass
class MonthlyOverview:
    """Monthly financial summary — one row per (month, source)."""

    __table__: ClassVar[str] = "monthly_overview"
    __pk__: ClassVar[tuple[str, ...]] = ("month", "source")

    month: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Month in YYYY-MM format",
            category="time",
        ),
    ]
    source: Source
    total_income: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total income for the month",
                unit="currency",
                example_value=5000.0,
                category="income",
                interpretation="Gross income before expenses; compare to total_spent for savings rate",
            ),
        ]
        | None
    ) = None
    total_spent: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total spending for the month",
                unit="currency",
                example_value=3200.0,
                category="spending",
                interpretation="Sum of all non-income transactions; lower is better relative to income",
            ),
        ]
        | None
    ) = None
    net: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Net cash flow (income minus spending)",
                unit="currency",
                example_value=1800.0,
                category="savings",
                interpretation="Positive = saving money; negative = spending more than earning",
            ),
        ]
        | None
    ) = None
    transaction_count: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Total number of transactions for the month",
                example_value=87,
                category="spending",
            ),
        ]
        | None
    ) = None
    savings_rate: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Percentage of income saved (net / income * 100)",
                unit="percent",
                value_range=(-100, 100),
                example_value=36.0,
                category="savings",
                interpretation="20%+ savings rate is a common target; negative means overspending relative to income",
            ),
        ]
        | None
    ) = None


ALL_TABLES = [Transaction, DailySpending, MonthlyCategory, MonthlyOverview]
