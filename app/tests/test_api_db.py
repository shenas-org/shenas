"""Tests for app.api.db -- helper functions called from GraphQL resolvers."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import duckdb
import pytest
from fastapi import HTTPException

from app.api import db as api_db


@pytest.fixture
def fake_db():
    """In-memory duckdb wired into app.api.db.cursor."""
    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA garmin")
    con.execute("CREATE TABLE garmin.activities (id INTEGER, date DATE)")
    con.execute("INSERT INTO garmin.activities VALUES (1, '2026-04-01'), (2, '2026-04-02')")
    con.execute("CREATE SCHEMA datasets")
    con.execute("CREATE TABLE datasets.fitness__daily_hrv (date DATE, value DOUBLE)")
    con.execute("INSERT INTO datasets.fitness__daily_hrv VALUES ('2026-04-01', 42.0)")

    @contextlib.contextmanager
    def _fake_cursor(**_kwargs):
        cur = con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with patch("app.api.db.cursor", _fake_cursor):
        yield con
    con.close()


class TestDiscoverSchemas:
    def test_returns_user_schemas(self, fake_db) -> None:
        schemas = api_db._discover_schemas()
        assert "garmin" in schemas
        assert "datasets" in schemas
        assert "activities" in schemas["garmin"]


class TestDbTables:
    def test_excludes_internal_schemas(self, fake_db) -> None:
        fake_db.execute("CREATE SCHEMA shenas")
        fake_db.execute("CREATE TABLE shenas.x (id INTEGER)")
        result = api_db.db_tables()
        assert "garmin" in result
        assert "shenas" not in result

    def test_swallows_failure(self) -> None:
        with patch("app.api.db._discover_schemas", side_effect=RuntimeError("nope")):
            assert api_db.db_tables() == {}


class TestSchemaPluginEndpoints:
    def test_schema_tables(self) -> None:
        with patch(
            "app.api.db._load_schema_plugins", return_value={"fitness": ["fitness__daily_hrv", "fitness__daily_sleep"]}
        ):
            result = api_db.schema_plugin_tables()
        assert result == {"datasets": ["fitness__daily_hrv", "fitness__daily_sleep"]}

    def test_schema_tables_empty(self) -> None:
        with patch("app.api.db._load_schema_plugins", return_value={}):
            assert api_db.schema_plugin_tables() == {}

    def test_schema_plugins(self) -> None:
        with patch("app.api.db._load_schema_plugins", return_value={"fitness": ["fitness__daily_hrv"]}):
            assert api_db.schema_plugin_ownership() == {"fitness": ["fitness__daily_hrv"]}

    def test_load_schema_plugins_uses_dataset_loader(self) -> None:
        fake_dataset = MagicMock(name="fitness")
        fake_dataset.name = "fitness"
        fake_dataset.tables = {"fitness__daily_hrv", "fitness__daily_sleep"}
        with patch("shenas_datasets.core.dataset.Dataset.load_all", return_value=[fake_dataset]):
            result = api_db._load_schema_plugins()
        assert result == {"fitness": ["fitness__daily_hrv", "fitness__daily_sleep"]}


class TestTablePreview:
    def test_returns_rows(self, fake_db) -> None:
        rows = api_db.table_preview("garmin", "activities")
        assert len(rows) == 2
        assert "id" in rows[0]

    def test_rejects_invalid_schema(self) -> None:
        with pytest.raises(HTTPException) as exc:
            api_db.table_preview("$bad", "table")
        assert exc.value.status_code == 400

    def test_rejects_invalid_table(self) -> None:
        with pytest.raises(HTTPException) as exc:
            api_db.table_preview("garmin", "$bad")
        assert exc.value.status_code == 400

    def test_limit_clamped_high(self, fake_db) -> None:
        rows = api_db.table_preview("garmin", "activities", limit=9999)
        assert len(rows) == 2  # only 2 rows in table

    def test_limit_clamped_low(self, fake_db) -> None:
        rows = api_db.table_preview("garmin", "activities", limit=0)
        # min is 1
        assert len(rows) == 1


class TestFlushSchema:
    def test_flushes_known_plugin(self, fake_db) -> None:
        with patch("app.api.db._load_schema_plugins", return_value={"fitness": ["fitness__daily_hrv"]}):
            result = api_db.flush_schema("fitness")
        assert result["schema"] == "fitness"
        assert result["rows_deleted"] == 1
        assert result["tables"] == ["fitness__daily_hrv"]

    def test_unknown_plugin_raises_404(self) -> None:
        with (
            patch("app.api.db._load_schema_plugins", return_value={}),
            pytest.raises(HTTPException) as exc,
        ):
            api_db.flush_schema("missing")
        assert exc.value.status_code == 404

    def test_skips_invalid_table_names(self, fake_db) -> None:
        with patch("app.api.db._load_schema_plugins", return_value={"fitness": ["$bad"]}):
            result = api_db.flush_schema("fitness")
        assert result["rows_deleted"] == 0

    def test_handles_missing_metric_tables(self, fake_db) -> None:
        with patch("app.api.db._load_schema_plugins", return_value={"fitness": ["nonexistent"]}):
            result = api_db.flush_schema("fitness")
        assert result["rows_deleted"] == 0


class TestKeygen:
    def test_generates_and_stores_key(self) -> None:
        with (
            patch("app.database.generate_db_key", return_value="newkey"),
            patch("app.database.set_db_key") as mock_set,
        ):
            result = api_db.db_keygen()
        assert result.ok is True
        mock_set.assert_called_once_with("newkey")
