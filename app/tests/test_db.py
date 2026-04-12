"""Tests for plugin state and database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest

if TYPE_CHECKING:
    import duckdb

from shenas_plugins.core.plugin import Plugin, PluginInstance


class _FakePlugin(Plugin):
    name = "garmin"
    display_name = "Garmin Connect"

    @property
    def _kind(self) -> str:
        return "source"


class _FakeTheme(Plugin):
    name = "dark"
    display_name = "Dark Theme"
    single_active: ClassVar[bool] = True

    @property
    def _kind(self) -> str:
        return "theme"


class TestCursorShim:
    def test_cursor_yields_connection(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.database import cursor

        with cursor() as cur:
            result = cur.execute("SELECT 1").fetchone()
        assert result == (1,)

    def test_cursor_with_database_tag(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.database import cursor

        with cursor(database="shenas") as cur:
            result = cur.execute("SELECT 1").fetchone()
        assert result == (1,)


class TestPluginState:
    def test_instance_creates_on_first_access(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        assert inst.kind == "source"
        assert inst.name == "garmin"
        assert inst.enabled is True

    def test_set_enabled_toggles(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.set_enabled(False)
        row = PluginInstance.find("source", "garmin")
        assert row is not None
        assert row.enabled is False
        inst.set_enabled(True)
        row = PluginInstance.find("source", "garmin")
        assert row is not None
        assert row.enabled is True

    def test_enable_disable(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.disable()
        row = PluginInstance.find("source", "garmin")
        assert row is not None
        assert row.enabled is False
        inst.enable()
        row = PluginInstance.find("source", "garmin")
        assert row is not None
        assert row.enabled is True

    def test_mark_synced(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.mark_synced()
        row = PluginInstance.find("source", "garmin")
        assert row is not None
        assert row.synced_at is not None

    def test_delete(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.delete()

        assert PluginInstance.find("source", "garmin") is None

    def test_multiple_kinds(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        _FakePlugin().get_or_create_instance()
        _FakeTheme().get_or_create_instance()

        source = PluginInstance.find("source", "garmin")
        theme = PluginInstance.find("theme", "dark")
        assert source is not None
        assert theme is not None
        assert source.kind == "source"
        assert theme.kind == "theme"

    def test_get_or_create_idempotent(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst1 = _FakePlugin().get_or_create_instance()
        inst2 = _FakePlugin().get_or_create_instance()
        assert inst1.kind == inst2.kind
        assert inst1.name == inst2.name


@pytest.mark.parametrize("full_refresh", [True, False])
def test_connect_read_only_ignored(full_refresh: bool, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
    """connect(read_only=...) currently ignores the flag but should not crash."""
    from app.database import connect

    con = connect(read_only=full_refresh)
    assert con is not None
