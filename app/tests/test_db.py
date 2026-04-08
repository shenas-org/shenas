"""Tests for app.db -- plugin state, workspace, hotkeys, transforms."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from shenas_plugins.core import Plugin


class _FakePlugin(Plugin):
    """Minimal plugin for testing state management."""

    name = "garmin"
    display_name = "Garmin"

    @property
    def _kind(self) -> str:
        return "source"


def _query_state(kind: str, name: str) -> dict | None:
    """Helper: look up a single plugin state via direct DB query."""
    from app.db import cursor

    with cursor() as cur:
        row = cur.execute(
            "SELECT kind, name, enabled, created_at, updated_at, status_changed_at, synced_at "
            "FROM shenas_system.plugins WHERE kind = ? AND name = ?",
            [kind, name],
        ).fetchone()
    if not row:
        return None
    return {
        "kind": row[0],
        "name": row[1],
        "enabled": row[2],
        "created_at": str(row[3]) if row[3] else None,
        "updated_at": str(row[4]) if row[4] else None,
        "status_changed_at": str(row[5]) if row[5] else None,
        "synced_at": str(row[6]) if row[6] else None,
    }


def _count_states() -> int:
    """Helper: count total plugin state rows."""
    from app.db import cursor

    with cursor() as cur:
        return cur.execute("SELECT count(*) FROM shenas_system.plugins").fetchone()[0]  # type: ignore[index]


class TestPluginState:
    def test_no_state_when_not_tracked(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        assert _FakePlugin().state is None

    def test_save_state_creates_new_plugin(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=True)
        state = p.state
        assert state is not None
        assert state.kind == "source"
        assert state.name == "garmin"
        assert state.enabled is True
        assert state.created_at is not None

    def test_save_state_updates_existing_same_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=True)
        first = p.state
        assert first is not None
        # update again with same enabled -- should just touch updated_at
        p.save_state(enabled=True)
        second = p.state
        assert second is not None
        assert second.enabled is True

    def test_save_state_toggles_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=True)
        p.save_state(enabled=False)
        state = p.state
        assert state is not None
        assert state.enabled is False
        assert state.status_changed_at is not None

    def test_remove_state(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=True)
        assert p.state is not None
        p.remove_state()
        assert p.state is None

    def test_remove_state_nonexistent_is_noop(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        # should not raise
        _FakePlugin().remove_state()

    def test_enabled_property_from_db(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=False)
        assert p.enabled is False
        p.save_state(enabled=True)
        assert p.enabled is True

    def test_enabled_property_default_when_no_state(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        assert _FakePlugin().enabled is True  # enabled_by_default = True

    def test_mark_synced(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.save_state(enabled=True)
        p.mark_synced()
        state = p.state
        assert state is not None
        assert state.synced_at is not None

    def test_mark_synced_creates_missing_state(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        p = _FakePlugin()
        p.mark_synced()
        state = p.state
        assert state is not None
        assert state.synced_at is not None

    def test_multiple_kinds(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        class _DatasetPlugin(Plugin):
            name = "fitness"
            display_name = "Fitness"

            @property
            def _kind(self) -> str:
                return "dataset"

        _FakePlugin().save_state(enabled=True)
        _DatasetPlugin().save_state(enabled=True)
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
