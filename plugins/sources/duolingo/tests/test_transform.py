from __future__ import annotations

from datetime import date

import duckdb
import pytest

from shenas_sources.core.transform import load_transform_defaults

TRANSFORM_DEFAULTS = load_transform_defaults("duolingo")


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("CREATE SCHEMA sources")
    db.execute("CREATE SCHEMA datasets")
    db.execute(
        "CREATE TABLE sources.duolingo__daily_xp (date VARCHAR, xp_gained INTEGER,"
        " num_sessions INTEGER, total_session_time_sec INTEGER)"
    )
    db.execute("CREATE TABLE datasets.daily_outcomes (date DATE, source VARCHAR, daily_duolingo_xp INTEGER)")
    db.execute("CREATE TABLE datasets.daily_habits (date DATE, source VARCHAR, duolingo BOOLEAN)")
    return db


class TestDuolingoDefaults:
    def test_xp_transform(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO sources.duolingo__daily_xp VALUES ('2026-03-28', 150, 3, 900)")
        t = TRANSFORM_DEFAULTS[0]
        con.execute(f"INSERT INTO datasets.daily_outcomes {t['sql']}")
        rows = con.execute("SELECT * FROM datasets.daily_outcomes").fetchall()
        assert len(rows) == 1
        assert rows[0] == (date(2026, 3, 28), "duolingo", 150)

    def test_habits_true_when_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO sources.duolingo__daily_xp VALUES ('2026-03-28', 150, 3, 900)")
        t = TRANSFORM_DEFAULTS[1]
        con.execute(f"INSERT INTO datasets.daily_habits {t['sql']}")
        rows = con.execute("SELECT duolingo FROM datasets.daily_habits").fetchall()
        assert rows == [(True,)]

    def test_habits_false_when_zero_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSERT INTO sources.duolingo__daily_xp VALUES ('2026-03-28', 0, 0, 0)")
        t = TRANSFORM_DEFAULTS[1]
        con.execute(f"INSERT INTO datasets.daily_habits {t['sql']}")
        rows = con.execute("SELECT duolingo FROM datasets.daily_habits").fetchall()
        assert rows == [(False,)]

    def test_defaults_have_descriptions(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t.get("description"), f"Missing description for {t['target_duckdb_table']}"
