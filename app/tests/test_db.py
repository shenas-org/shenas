"""Tests for app.db -- plugin state, workspace, hotkeys, transforms."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from shenas_plugins.core import Plugin
from shenas_plugins.core.plugin import PluginInstance


class _FakePlugin(Plugin):
    """Minimal plugin for testing state management."""

    name = "garmin"
    display_name = "Garmin"

    @property
    def _kind(self) -> str:
        return "source"


def _query_state(kind: str, name: str) -> dict | None:
    """Helper: look up a single plugin state via direct DB query."""
    from app.database import cursor

    with cursor() as cur:
        row = cur.execute(
            "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
            "FROM shenas_system.plugins WHERE kind = ? AND name = ?",
            [kind, name],
        ).fetchone()
    if not row:
        return None
    return {
        "kind": row[0],
        "name": row[1],
        "enabled": row[2],
        "added_at": str(row[3]) if row[3] else None,
        "updated_at": str(row[4]) if row[4] else None,
        "status_changed_at": str(row[5]) if row[5] else None,
        "synced_at": str(row[6]) if row[6] else None,
    }


def _count_states() -> int:
    """Helper: count total plugin state rows."""
    from app.database import cursor

    with cursor() as cur:
        return cur.execute("SELECT count(*) FROM shenas_system.plugins").fetchone()[0]  # ty: ignore[not-subscriptable]


class TestPluginState:
    def test_instance_creates_on_first_access(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        assert inst.kind == "source"  # ty: ignore[unresolved-attribute]
        assert inst.name == "garmin"  # ty: ignore[unresolved-attribute]
        assert inst.enabled is True  # ty: ignore[unresolved-attribute]

    def test_set_enabled_toggles(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.set_enabled(False)  # ty: ignore[unresolved-attribute]
        assert PluginInstance.find("source", "garmin").enabled is False  # ty: ignore[unresolved-attribute]
        inst.set_enabled(True)  # ty: ignore[unresolved-attribute]
        assert PluginInstance.find("source", "garmin").enabled is True  # ty: ignore[unresolved-attribute]

    def test_enable_disable(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.disable()  # ty: ignore[unresolved-attribute]
        assert PluginInstance.find("source", "garmin").enabled is False  # ty: ignore[unresolved-attribute]
        inst.enable()  # ty: ignore[unresolved-attribute]
        assert PluginInstance.find("source", "garmin").enabled is True  # ty: ignore[unresolved-attribute]

    def test_mark_synced(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.mark_synced()  # ty: ignore[unresolved-attribute]
        row = PluginInstance.find("source", "garmin")
        assert row.synced_at is not None  # ty: ignore[unresolved-attribute]

    def test_delete(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        inst = _FakePlugin().get_or_create_instance()
        inst.delete()  # ty: ignore[unresolved-attribute]

        assert PluginInstance.find("source", "garmin") is None

    def test_multiple_kinds(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        _FakePlugin().get_or_create_instance()
        PluginInstance.get_or_create("dataset", "fitness")
        assert _count_states() == 2
        assert _query_state("source", "garmin") is not None
        assert _query_state("dataset", "fitness") is not None


class TestWorkspace:
    def test_get_empty_by_default(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.workspace import Workspace

        assert Workspace.get() == {}

    def test_save_and_get(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.workspace import Workspace

        state = {"tabs": ["dashboard", "settings"], "active": 0}
        Workspace.put(state)
        assert Workspace.get() == state

    def test_save_overwrites(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.workspace import Workspace

        Workspace.put({"first": True})
        Workspace.put({"second": True})
        assert Workspace.get() == {"second": True}


class TestHotkeys:
    def test_default_hotkeys_seeded(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.hotkeys import Hotkey

        hotkeys = Hotkey.get_all()
        assert "command-palette" in hotkeys
        assert hotkeys["command-palette"] == "Ctrl+P"
        assert "close-tab" in hotkeys

    def test_set_new(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.hotkeys import Hotkey

        Hotkey(action_id="custom-action").set_binding("Ctrl+Shift+X")
        assert Hotkey.get_all()["custom-action"] == "Ctrl+Shift+X"

    def test_set_overwrite(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.hotkeys import Hotkey

        Hotkey(action_id="command-palette").set_binding("Ctrl+Shift+P")
        assert Hotkey.get_all()["command-palette"] == "Ctrl+Shift+P"

    def test_delete(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.hotkeys import Hotkey

        Hotkey(action_id="command-palette").delete()
        assert "command-palette" not in Hotkey.get_all()

    def test_reset(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.hotkeys import Hotkey

        Hotkey(action_id="command-palette").set_binding("Ctrl+Shift+P")
        Hotkey(action_id="custom-action").set_binding("Ctrl+X")
        Hotkey.reset()
        hotkeys = Hotkey.get_all()
        assert hotkeys["command-palette"] == "Ctrl+P"
        assert "custom-action" not in hotkeys
