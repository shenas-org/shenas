"""Tests for app.transforms.Transform CRUD, seeding, execution."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Per-test isolated in-memory DuckDB with system tables."""
    con = duckdb.connect(":memory:")
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    from app.db import _ensure_system_tables

    _ensure_system_tables(con)
    con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
    yield con
    con.close()


@pytest.fixture(autouse=True)
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    """Route app.db.cursor through db_con for the duration of each test."""

    @contextlib.contextmanager
    def _fake_cursor(**_kwargs) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = db_con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with patch("app.db.cursor", _fake_cursor), patch("app.transforms.cursor", _fake_cursor):
        yield


def _make(
    plugin: str = "garmin",
    src_table: str = "activities",
    tgt_table: str = "daily_activities",
    sql: str = "SELECT 1 AS id",
    **kw,
):
    from app.transforms import Transform

    return Transform.create(
        source_duckdb_schema="garmin",
        source_duckdb_table=src_table,
        target_duckdb_schema="metrics",
        target_duckdb_table=tgt_table,
        source_plugin=plugin,
        sql=sql,
        **kw,
    )


class TestTransformCRUD:
    def test_all_empty(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        assert TransformInstance.all() == []

    def test_find_none(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        assert TransformInstance.find(9999) is None

    def test_create_and_find(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        t = _make(description="hello")
        assert t.id >= 1
        assert t.sql == "SELECT 1 AS id"
        assert t.enabled is True
        assert t.is_default is False
        assert t.description == "hello"
        assert t.source_plugin == "garmin"
        assert t.to_dict()["sql"] == "SELECT 1 AS id"

        found = TransformInstance.find(t.id)
        assert found is not None
        assert found.id == t.id

    def test_all_filter_by_plugin(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        _make(plugin="garmin", src_table="a", tgt_table="ta")
        _make(plugin="lunchmoney", src_table="b", tgt_table="tb")
        assert len(TransformInstance.all()) == 2
        only_g = TransformInstance.for_plugin("garmin")
        assert len(only_g) == 1
        assert only_g[0].source_plugin == "garmin"

    def test_update(self, db_con: duckdb.DuckDBPyConnection) -> None:
        t = _make()
        updated = t.update("SELECT 2 AS new_col")
        assert updated.sql == "SELECT 2 AS new_col"
        assert updated.updated_at is not None

    def test_delete_user_transform(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        t = _make()
        t.delete()
        assert TransformInstance.find(t.id) is None

    def test_delete_default_blocked(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import TransformInstance

        t = _make(is_default=True)
        t.delete()
        assert TransformInstance.find(t.id) is not None

    def test_set_enabled_toggle(self, db_con: duckdb.DuckDBPyConnection) -> None:
        t = _make()
        disabled = t.set_enabled(False)
        assert disabled.enabled is False
        assert disabled.status_changed_at is not None
        enabled = disabled.set_enabled(True)
        assert enabled.enabled is True

    def test_test_runs_sql(self, db_con: duckdb.DuckDBPyConnection) -> None:
        t = _make(sql="SELECT 1 AS a, 'x' AS b")
        rows = t.test(limit=5)
        assert rows == [{"a": 1, "b": "x"}]


class TestSeedDefaults:
    def test_seed_inserts(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform, TransformInstance

        defaults = [
            {
                "source_duckdb_schema": "garmin",
                "source_duckdb_table": "activities",
                "target_duckdb_schema": "metrics",
                "target_duckdb_table": "daily_activities",
                "sql": "SELECT 1",
                "description": "d",
            }
        ]
        Transform.seed_defaults("garmin", defaults)
        all_t = TransformInstance.for_plugin("garmin")
        assert len(all_t) == 1
        assert all_t[0].is_default is True
        assert all_t[0].description == "d"

    def test_seed_idempotent_updates(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform, TransformInstance

        defaults = [
            {
                "source_duckdb_schema": "garmin",
                "source_duckdb_table": "activities",
                "target_duckdb_schema": "metrics",
                "target_duckdb_table": "daily_activities",
                "sql": "SELECT 1",
                "description": "v1",
            }
        ]
        Transform.seed_defaults("garmin", defaults)
        defaults[0]["sql"] = "SELECT 2"
        defaults[0]["description"] = "v2"
        Transform.seed_defaults("garmin", defaults)

        all_t = TransformInstance.for_plugin("garmin")
        assert len(all_t) == 1
        assert all_t[0].sql == "SELECT 2"
        assert all_t[0].description == "v2"


class TestExecution:
    def _setup_target(self, db_con: duckdb.DuckDBPyConnection) -> None:
        db_con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
        db_con.execute("CREATE TABLE IF NOT EXISTS metrics.daily_activities (id INTEGER, source VARCHAR)")

    def test_run_for_source_executes_enabled(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform

        self._setup_target(db_con)
        _make(sql="SELECT 1 AS id, 'garmin' AS source")
        t2 = _make(src_table="b", tgt_table="daily_activities", sql="SELECT 2 AS id, 'garmin' AS source")
        t2.set_enabled(False)

        count = Transform.run_for_source(db_con, "garmin")
        assert count == 1
        rows = db_con.execute("SELECT id FROM metrics.daily_activities ORDER BY id").fetchall()
        assert rows == [(1,)]

    def test_run_for_source_no_transforms(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform

        assert Transform.run_for_source(db_con, "missing") == 0

    def test_run_for_target(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform

        self._setup_target(db_con)
        _make(sql="SELECT 7 AS id, 'garmin' AS source")
        count = Transform.run_for_target(db_con, "daily_activities")
        assert count == 1
        rows = db_con.execute("SELECT id FROM metrics.daily_activities").fetchall()
        assert rows == [(7,)]

    def test_run_for_source_handles_bad_sql(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.transforms import Transform

        self._setup_target(db_con)
        _make(sql="SELECT * FROM nonexistent_table_xyz")
        count = Transform.run_for_source(db_con, "garmin")
        assert count == 0
