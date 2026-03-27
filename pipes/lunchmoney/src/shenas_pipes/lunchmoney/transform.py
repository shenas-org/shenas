import duckdb

from shenas_pipes.core.transform import MetricProviderBase


class LunchMoneyMetricProvider(MetricProviderBase):
    source = "lunchmoney"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._transactions(con)
        self._daily_spending(con)
        self._monthly_category(con)
        self._monthly_overview(con)

    def _transactions(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "transactions",
            """
            INSERT INTO metrics.transactions
                (id, source, date, amount, payee, category, category_group, account, currency, is_income, notes, recurring)
            SELECT
                id::VARCHAR,
                'lunchmoney',
                date::DATE,
                CASE WHEN is_income THEN ABS(to_base) ELSE -ABS(to_base) END,
                payee,
                category_name,
                category_group_name,
                COALESCE(account_display_name, plaid_account_name),
                currency,
                CASE WHEN is_income THEN 1 ELSE 0 END,
                display_notes,
                CASE WHEN recurring_id IS NOT NULL THEN 1 ELSE 0 END
            FROM lunchmoney.transactions
            WHERE status != 'pending'
            """,
        )

    def _daily_spending(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_spending",
            """
            INSERT INTO metrics.daily_spending (date, source, total_spent, total_income, transaction_count)
            SELECT
                date::DATE,
                'lunchmoney',
                SUM(CASE WHEN NOT is_income THEN ABS(to_base) ELSE 0 END),
                SUM(CASE WHEN is_income THEN ABS(to_base) ELSE 0 END),
                COUNT(*)
            FROM lunchmoney.transactions
            WHERE status != 'pending'
            GROUP BY date
            """,
        )

    def _monthly_category(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "monthly_category",
            """
            INSERT INTO metrics.monthly_category (month, category, source, amount_spent, transaction_count)
            SELECT
                STRFTIME(date::DATE, '%Y-%m'),
                COALESCE(category_name, 'Uncategorized'),
                'lunchmoney',
                SUM(ABS(to_base)),
                COUNT(*)
            FROM lunchmoney.transactions
            WHERE status != 'pending' AND NOT is_income
            GROUP BY STRFTIME(date::DATE, '%Y-%m'), COALESCE(category_name, 'Uncategorized')
            """,
        )

    def _monthly_overview(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "monthly_overview",
            """
            INSERT INTO metrics.monthly_overview
                (month, source, total_income, total_spent, net, transaction_count, savings_rate)
            SELECT
                STRFTIME(date::DATE, '%Y-%m'),
                'lunchmoney',
                SUM(CASE WHEN is_income THEN ABS(to_base) ELSE 0 END),
                SUM(CASE WHEN NOT is_income THEN ABS(to_base) ELSE 0 END),
                SUM(CASE WHEN is_income THEN ABS(to_base) ELSE -ABS(to_base) END),
                COUNT(*),
                CASE
                    WHEN SUM(CASE WHEN is_income THEN ABS(to_base) ELSE 0 END) > 0
                    THEN (SUM(CASE WHEN is_income THEN ABS(to_base) ELSE -ABS(to_base) END)
                          / SUM(CASE WHEN is_income THEN ABS(to_base) ELSE 0 END)) * 100
                    ELSE NULL
                END
            FROM lunchmoney.transactions
            WHERE status != 'pending'
            GROUP BY STRFTIME(date::DATE, '%Y-%m')
            """,
        )
