import duckdb
import pytest

from shenas_pipes.lunchmoney.transform import LunchMoneyMetricProvider


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with raw lunchmoney tables and canonical metrics schema."""
    db = duckdb.connect(":memory:")

    # Create raw lunchmoney schema with test data
    db.execute("CREATE SCHEMA lunchmoney")
    db.execute("""
        CREATE TABLE lunchmoney.transactions (
            id INTEGER,
            date VARCHAR,
            to_base DOUBLE,
            payee VARCHAR,
            category_name VARCHAR,
            category_group_name VARCHAR,
            account_display_name VARCHAR,
            plaid_account_name VARCHAR,
            currency VARCHAR,
            is_income BOOLEAN,
            display_notes VARCHAR,
            recurring_id INTEGER,
            status VARCHAR
        )
    """)
    db.execute("""
        INSERT INTO lunchmoney.transactions VALUES
            (1, '2026-03-15', 42.50, 'Grocery Store', 'Groceries', 'Food', 'Checking', NULL, 'USD', false, NULL, NULL, 'cleared'),
            (2, '2026-03-15', 15.00, 'Coffee Shop', 'Coffee', 'Food', NULL, 'Chase Card', 'USD', false, 'morning coffee', NULL, 'cleared'),
            (3, '2026-03-16', 5000.00, 'Employer Inc', 'Salary', 'Income', 'Checking', NULL, 'USD', true, NULL, 100, 'cleared'),
            (4, '2026-03-16', 100.00, 'Pending Store', 'Shopping', 'Retail', 'Checking', NULL, 'USD', false, NULL, NULL, 'pending')
    """)

    # Create canonical metrics schema
    db.execute("CREATE SCHEMA metrics")
    db.execute("""
        CREATE TABLE metrics.transactions (
            id VARCHAR NOT NULL, source VARCHAR NOT NULL, date DATE, amount DOUBLE,
            payee VARCHAR, category VARCHAR, category_group VARCHAR, account VARCHAR,
            currency VARCHAR, is_income INTEGER, notes VARCHAR, recurring INTEGER,
            PRIMARY KEY (id, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_spending (
            date DATE NOT NULL, source VARCHAR NOT NULL, total_spent DOUBLE,
            total_income DOUBLE, transaction_count INTEGER,
            PRIMARY KEY (date, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.monthly_category (
            month VARCHAR NOT NULL, category VARCHAR NOT NULL, source VARCHAR NOT NULL,
            amount_spent DOUBLE, transaction_count INTEGER, budget_amount DOUBLE,
            PRIMARY KEY (month, category, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.monthly_overview (
            month VARCHAR NOT NULL, source VARCHAR NOT NULL, total_income DOUBLE,
            total_spent DOUBLE, net DOUBLE, transaction_count INTEGER, savings_rate DOUBLE,
            PRIMARY KEY (month, source)
        )
    """)

    return db


class TestLunchMoneyTransform:
    def test_transactions_excludes_pending(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.transactions ORDER BY id").fetchall()
        assert len(rows) == 3
        ids = [r[0] for r in rows]
        assert "4" not in ids

    def test_transactions_amount_sign(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT id, amount FROM metrics.transactions ORDER BY id").fetchall()
        assert rows[0][1] == -42.50  # expense is negative
        assert rows[2][1] == 5000.00  # income is positive

    def test_transactions_account_coalesce(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT id, account FROM metrics.transactions ORDER BY id").fetchall()
        assert rows[0][1] == "Checking"  # from account_display_name
        assert rows[1][1] == "Chase Card"  # from plaid_account_name

    def test_transactions_recurring_flag(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT id, recurring FROM metrics.transactions ORDER BY id").fetchall()
        assert rows[0][1] == 0  # no recurring_id
        assert rows[2][1] == 1  # has recurring_id=100

    def test_daily_spending(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_spending ORDER BY date").fetchall()
        assert len(rows) == 2
        # March 15: 42.50 + 15.00 spent, 0 income, 2 txns
        assert rows[0][2] == pytest.approx(57.50)
        assert rows[0][3] == 0.0
        assert rows[0][4] == 2
        # March 16: 0 spent (pending excluded), 5000 income, 1 txn
        assert rows[1][2] == 0.0
        assert rows[1][3] == 5000.0
        assert rows[1][4] == 1

    def test_monthly_category(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.monthly_category ORDER BY category").fetchall()
        assert len(rows) == 2  # Coffee, Groceries (income excluded)
        categories = [r[1] for r in rows]
        assert "Coffee" in categories
        assert "Groceries" in categories

    def test_monthly_overview(self, con: duckdb.DuckDBPyConnection) -> None:
        LunchMoneyMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.monthly_overview").fetchall()
        assert len(rows) == 1
        assert rows[0][2] == 5000.0  # total_income
        assert rows[0][3] == pytest.approx(57.50)  # total_spent
        assert rows[0][4] == pytest.approx(5000.0 - 57.50)  # net
        assert rows[0][5] == 3  # transaction_count

    def test_idempotent(self, con: duckdb.DuckDBPyConnection) -> None:
        provider = LunchMoneyMetricProvider()
        provider.transform(con)
        provider.transform(con)
        rows = con.execute("SELECT * FROM metrics.transactions").fetchall()
        assert len(rows) == 3

    def test_source_tag(self) -> None:
        assert LunchMoneyMetricProvider.source == "lunchmoney"
