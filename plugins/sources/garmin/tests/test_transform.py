from __future__ import annotations

from datetime import date

import duckdb
import pytest

from shenas_sources.core.transform import load_transform_defaults

TRANSFORM_DEFAULTS = load_transform_defaults("garmin")


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("CREATE SCHEMA sources")
    db.execute("CREATE SCHEMA datasets")
    db.execute("CREATE TABLE sources.garmin__hrv (calendar_date VARCHAR, hrv_summary__last_night_avg DOUBLE)")
    db.execute(
        "CREATE TABLE sources.garmin__daily_stats (calendar_date VARCHAR,"
        " resting_heart_rate INTEGER, total_steps INTEGER, active_kilocalories DOUBLE)"
    )
    db.execute("CREATE TABLE datasets.daily_hrv (date DATE, source VARCHAR, rmssd DOUBLE)")
    db.execute(
        "CREATE TABLE datasets.daily_vitals"
        " (date DATE, source VARCHAR, resting_hr INTEGER, steps INTEGER, active_kcal INTEGER)"
    )
    return db


class TestGarminDefaults:
    def test_hrv_transform(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO sources.garmin__hrv VALUES ('2026-03-15', 42.0)")
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO datasets.daily_hrv {t['sql']}")
        rows = con.execute("SELECT * FROM datasets.daily_hrv").fetchall()
        assert len(rows) == 1
        assert rows[0] == (date(2026, 3, 15), "garmin", 42.0)

    def test_vitals_transform(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO sources.garmin__daily_stats VALUES ('2026-03-15', 55, 10000, 350.0)")
        t = TRANSFORM_DEFAULTS[2]
        con.execute(f"INSERT INTO datasets.daily_vitals {t['sql']}")
        rows = con.execute("SELECT * FROM datasets.daily_vitals").fetchall()
        assert len(rows) == 1
        assert rows[0] == (date(2026, 3, 15), "garmin", 55, 10000, 350)

    def test_defaults_have_descriptions(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t.get("description"), f"Missing description for {t['target_duckdb_table']}"
