from __future__ import annotations

from datetime import date

import duckdb
import pytest

from shenas_pipes.strava.transform import StravaMetricProvider


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("CREATE SCHEMA IF NOT EXISTS strava")
    db.execute("CREATE SCHEMA IF NOT EXISTS metrics")
    db.execute("""
        CREATE TABLE strava.activities (
            id BIGINT,
            start_date_local VARCHAR,
            kilojoules DOUBLE
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_vitals (
            date DATE,
            source VARCHAR,
            resting_hr INTEGER,
            steps INTEGER,
            active_kcal INTEGER
        )
    """)
    return db


class TestStravaTransform:
    def test_aggregates_kilojoules_to_kcal(self, con: duckdb.DuckDBPyConnection) -> None:
        # 1464 kJ + 836 kJ = 2300 kJ / 4.184 = 549 kcal
        con.execute("""
            INSERT INTO strava.activities VALUES
                (1, '2026-03-28T09:00:00Z', 1464),
                (2, '2026-03-28T17:00:00Z', 836),
                (3, '2026-03-29T09:00:00Z', 2092)
        """)

        provider = StravaMetricProvider()
        provider.transform(con)

        rows = con.execute("SELECT date, active_kcal FROM metrics.daily_vitals ORDER BY date").fetchall()
        assert len(rows) == 2
        assert rows[0] == (date(2026, 3, 28), 550)
        assert rows[1] == (date(2026, 3, 29), 500)

    def test_idempotent(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO strava.activities VALUES (1, '2026-03-28T09:00:00Z', 1464)")

        provider = StravaMetricProvider()
        provider.transform(con)
        provider.transform(con)

        rows = con.execute("SELECT * FROM metrics.daily_vitals").fetchall()
        assert len(rows) == 1
