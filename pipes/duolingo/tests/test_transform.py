from __future__ import annotations

import duckdb
import pytest

from shenas_pipes.duolingo.transform import DuolingoMetricProvider


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("CREATE SCHEMA IF NOT EXISTS duolingo")
    db.execute("CREATE SCHEMA IF NOT EXISTS metrics")
    db.execute("""
        CREATE TABLE duolingo.daily_xp (
            date VARCHAR,
            xp_gained INTEGER,
            num_sessions INTEGER,
            total_session_time_sec INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_outcomes (
            date DATE,
            source VARCHAR,
            daily_duolingo_xp INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_habits (
            date DATE,
            source VARCHAR,
            duolingo BOOLEAN
        )
    """)
    return db


class TestDuolingoTransform:
    def test_inserts_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("""
            INSERT INTO duolingo.daily_xp VALUES
                ('2026-03-28', 150, 3, 900),
                ('2026-03-29', 80, 2, 600)
        """)

        provider = DuolingoMetricProvider()
        provider.transform(con)

        rows = con.execute("SELECT * FROM metrics.daily_outcomes ORDER BY date").fetchall()
        assert len(rows) == 2
        from datetime import date

        assert rows[0] == (date(2026, 3, 28), "duolingo", 150)
        assert rows[1] == (date(2026, 3, 29), "duolingo", 80)

    def test_skips_null_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO duolingo.daily_xp VALUES ('2026-03-28', NULL, 0, 0)")

        provider = DuolingoMetricProvider()
        provider.transform(con)

        rows = con.execute("SELECT * FROM metrics.daily_outcomes").fetchall()
        assert len(rows) == 0

    def test_idempotent(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO duolingo.daily_xp VALUES ('2026-03-28', 150, 3, 900)")

        provider = DuolingoMetricProvider()
        provider.transform(con)
        provider.transform(con)

        rows = con.execute("SELECT * FROM metrics.daily_outcomes").fetchall()
        assert len(rows) == 1

    def test_habits_true_when_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO duolingo.daily_xp VALUES ('2026-03-28', 150, 3, 900)")

        provider = DuolingoMetricProvider()
        provider.transform(con)

        rows = con.execute("SELECT duolingo FROM metrics.daily_habits").fetchall()
        assert rows == [(True,)]

    def test_habits_false_when_zero_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO duolingo.daily_xp VALUES ('2026-03-28', 0, 0, 0)")

        provider = DuolingoMetricProvider()
        provider.transform(con)

        rows = con.execute("SELECT duolingo FROM metrics.daily_habits").fetchall()
        assert rows == [(False,)]
