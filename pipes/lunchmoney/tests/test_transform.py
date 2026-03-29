from __future__ import annotations


import duckdb
import pytest

from shenas_pipes.core.transform import load_transform_defaults

TRANSFORM_DEFAULTS = load_transform_defaults("lunchmoney")


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("CREATE SCHEMA lunchmoney")
    db.execute("CREATE SCHEMA metrics")
    db.execute("""
        CREATE TABLE lunchmoney.transactions (
            id INTEGER, date VARCHAR, payee VARCHAR, amount DOUBLE, to_base DOUBLE,
            category_name VARCHAR, category_group_name VARCHAR,
            account_display_name VARCHAR, plaid_account_name VARCHAR,
            currency VARCHAR, is_income BOOLEAN, display_notes VARCHAR,
            recurring_id INTEGER, status VARCHAR
        )
    """)
    db.execute("""
        CREATE TABLE metrics.transactions (
            id VARCHAR, source VARCHAR, date DATE, amount DOUBLE, payee VARCHAR,
            category VARCHAR, category_group VARCHAR, account VARCHAR,
            currency VARCHAR, is_income INTEGER, notes VARCHAR, recurring INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_spending (
            date DATE, source VARCHAR, total_spent DOUBLE,
            total_income DOUBLE, transaction_count BIGINT
        )
    """)
    db.execute("""
        CREATE TABLE metrics.monthly_category (
            month VARCHAR, category VARCHAR, source VARCHAR,
            amount_spent DOUBLE, transaction_count BIGINT
        )
    """)
    db.execute("""
        CREATE TABLE metrics.monthly_overview (
            month VARCHAR, source VARCHAR, total_income DOUBLE,
            total_spent DOUBLE, net DOUBLE, transaction_count BIGINT,
            savings_rate DOUBLE
        )
    """)
    return db


def _insert_txn(con: duckdb.DuckDBPyConnection, **overrides: object) -> None:
    defaults = {
        "id": 1,
        "date": "2026-03-15",
        "payee": "Store",
        "amount": -50.0,
        "to_base": 50.0,
        "category_name": "Food",
        "category_group_name": "Essentials",
        "account_display_name": "Checking",
        "plaid_account_name": None,
        "currency": "USD",
        "is_income": False,
        "display_notes": None,
        "recurring_id": None,
        "status": "cleared",
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join(["?"] * len(defaults))
    con.execute(f"INSERT INTO lunchmoney.transactions ({cols}) VALUES ({placeholders})", list(defaults.values()))


class TestLunchmoneyDefaults:
    def test_has_four_transforms(self) -> None:
        assert len(TRANSFORM_DEFAULTS) == 4

    def test_defaults_have_descriptions(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t.get("description"), f"Missing description for {t['target_duckdb_table']}"

    def test_all_target_metrics_schema(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t["target_duckdb_schema"] == "metrics"


class TestTransactionsTransform:
    def test_expense_amount_is_negative(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, is_income=False, to_base=50.0)
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO metrics.transactions {t['sql']}")
        row = con.execute("SELECT amount, is_income FROM metrics.transactions").fetchone()
        assert row[0] == -50.0
        assert row[1] == 0

    def test_income_amount_is_positive(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, id=2, is_income=True, to_base=1000.0)
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO metrics.transactions {t['sql']}")
        row = con.execute("SELECT amount, is_income FROM metrics.transactions").fetchone()
        assert row[0] == 1000.0
        assert row[1] == 1

    def test_pending_excluded(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, status="pending")
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO metrics.transactions {t['sql']}")
        rows = con.execute("SELECT * FROM metrics.transactions").fetchall()
        assert len(rows) == 0

    def test_account_coalesce(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, account_display_name=None, plaid_account_name="Plaid Acct")
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO metrics.transactions {t['sql']}")
        row = con.execute("SELECT account FROM metrics.transactions").fetchone()
        assert row[0] == "Plaid Acct"


class TestDailySpendingTransform:
    def test_aggregation(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, id=1, is_income=False, to_base=30.0)
        _insert_txn(con, id=2, is_income=False, to_base=20.0)
        _insert_txn(con, id=3, is_income=True, to_base=500.0)
        t = TRANSFORM_DEFAULTS[1]
        con.execute(f"INSERT INTO metrics.daily_spending {t['sql']}")
        row = con.execute("SELECT total_spent, total_income, transaction_count FROM metrics.daily_spending").fetchone()
        assert row[0] == 50.0
        assert row[1] == 500.0
        assert row[2] == 3


class TestMonthlyCategoryTransform:
    def test_groups_by_category(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, id=1, category_name="Food", is_income=False, to_base=30.0)
        _insert_txn(con, id=2, category_name="Food", is_income=False, to_base=20.0)
        _insert_txn(con, id=3, category_name="Transport", is_income=False, to_base=10.0)
        t = TRANSFORM_DEFAULTS[2]
        con.execute(f"INSERT INTO metrics.monthly_category {t['sql']}")
        rows = con.execute("SELECT category, amount_spent FROM metrics.monthly_category ORDER BY category").fetchall()
        assert len(rows) == 2
        assert rows[0] == ("Food", 50.0)
        assert rows[1] == ("Transport", 10.0)

    def test_excludes_income(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, id=1, is_income=True, to_base=1000.0, category_name="Salary")
        t = TRANSFORM_DEFAULTS[2]
        con.execute(f"INSERT INTO metrics.monthly_category {t['sql']}")
        rows = con.execute("SELECT * FROM metrics.monthly_category").fetchall()
        assert len(rows) == 0


class TestMonthlyOverviewTransform:
    def test_savings_rate(self, con: duckdb.DuckDBPyConnection) -> None:
        _insert_txn(con, id=1, is_income=True, to_base=1000.0)
        _insert_txn(con, id=2, is_income=False, to_base=400.0)
        t = TRANSFORM_DEFAULTS[3]
        con.execute(f"INSERT INTO metrics.monthly_overview {t['sql']}")
        row = con.execute("SELECT total_income, total_spent, net, savings_rate FROM metrics.monthly_overview").fetchone()
        assert row[0] == 1000.0
        assert row[1] == 400.0
        assert row[2] == 600.0
        assert row[3] == pytest.approx(60.0)
