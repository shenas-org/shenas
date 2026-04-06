"""Tests for app.db -- plugin state, workspace, hotkeys, transforms."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import duckdb


class TestPluginState:
    def test_get_plugin_state_returns_none_when_not_tracked(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state

        assert get_plugin_state("pipe", "nonexistent") is None

    def test_upsert_creates_new_plugin(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        state = get_plugin_state("pipe", "garmin")
        assert state is not None
        assert state["kind"] == "pipe"
        assert state["name"] == "garmin"
        assert state["enabled"] is True
        assert state["added_at"] is not None

    def test_upsert_updates_existing_same_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        first = get_plugin_state("pipe", "garmin")
        assert first is not None
        # update again with same enabled -- should just touch updated_at
        upsert_plugin_state("pipe", "garmin", enabled=True)
        second = get_plugin_state("pipe", "garmin")
        assert second is not None
        assert second["enabled"] is True

    def test_upsert_toggles_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        upsert_plugin_state("pipe", "garmin", enabled=False)
        state = get_plugin_state("pipe", "garmin")
        assert state is not None
        assert state["enabled"] is False
        assert state["status_changed_at"] is not None

    def test_remove_plugin_state(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, remove_plugin_state, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        assert get_plugin_state("pipe", "garmin") is not None
        remove_plugin_state("pipe", "garmin")
        assert get_plugin_state("pipe", "garmin") is None

    def test_remove_nonexistent_is_noop(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import remove_plugin_state

        # should not raise
        remove_plugin_state("pipe", "nonexistent")


class TestIsPluginEnabled:
    def test_returns_true_when_not_tracked(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import is_plugin_enabled

        assert is_plugin_enabled("pipe", "unknown") is True

    def test_returns_true_when_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import is_plugin_enabled, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        assert is_plugin_enabled("pipe", "garmin") is True

    def test_returns_false_when_disabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import is_plugin_enabled, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=False)
        assert is_plugin_enabled("pipe", "garmin") is False


class TestGetAllPluginStates:
    def test_empty_when_no_plugins(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_all_plugin_states

        assert get_all_plugin_states() == []

    def test_returns_all_plugins(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_all_plugin_states, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        upsert_plugin_state("schema", "fitness", enabled=True)
        states = get_all_plugin_states()
        assert len(states) == 2
        names = {s["name"] for s in states}
        assert names == {"garmin", "fitness"}

    def test_filter_by_kind(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_all_plugin_states, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        upsert_plugin_state("schema", "fitness", enabled=True)
        pipes = get_all_plugin_states(kind="pipe")
        assert len(pipes) == 1
        assert pipes[0]["name"] == "garmin"


class TestWorkspace:
    def test_get_workspace_empty_by_default(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_workspace

        assert get_workspace() == {}

    def test_save_and_get_workspace(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_workspace, save_workspace

        state = {"tabs": ["dashboard", "settings"], "active": 0}
        save_workspace(state)
        result = get_workspace()
        assert result == state

    def test_save_workspace_overwrites(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_workspace, save_workspace

        save_workspace({"first": True})
        save_workspace({"second": True})
        result = get_workspace()
        assert result == {"second": True}


class TestHotkeys:
    def test_default_hotkeys_seeded(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_hotkeys

        hotkeys = get_hotkeys()
        assert "command-palette" in hotkeys
        assert hotkeys["command-palette"] == "Ctrl+P"
        assert "close-tab" in hotkeys

    def test_set_hotkey_new(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_hotkeys, set_hotkey

        set_hotkey("custom-action", "Ctrl+Shift+X")
        hotkeys = get_hotkeys()
        assert hotkeys["custom-action"] == "Ctrl+Shift+X"

    def test_set_hotkey_overwrite(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_hotkeys, set_hotkey

        set_hotkey("command-palette", "Ctrl+Shift+P")
        hotkeys = get_hotkeys()
        assert hotkeys["command-palette"] == "Ctrl+Shift+P"

    def test_delete_hotkey(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import delete_hotkey, get_hotkeys

        delete_hotkey("command-palette")
        hotkeys = get_hotkeys()
        assert "command-palette" not in hotkeys

    def test_reset_hotkeys(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_hotkeys, reset_hotkeys, set_hotkey

        set_hotkey("command-palette", "Ctrl+Shift+P")
        set_hotkey("custom-action", "Ctrl+X")
        reset_hotkeys()
        hotkeys = get_hotkeys()
        assert hotkeys["command-palette"] == "Ctrl+P"
        assert "custom-action" not in hotkeys


@pytest.mark.skipif(True, reason="Transform tests need per-test DB isolation (sequence state)")
class TestTransformCRUD:
    """Test transforms via the app.transforms module, which uses app.db.connect."""

    def test_list_transforms_empty(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import list_transforms

        assert list_transforms() == []

    def test_create_and_get_transform(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, get_transform

        t = create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1 AS id",
            description="test transform",
        )
        assert t["id"] >= 1
        assert t["source_plugin"] == "garmin"
        assert t["description"] == "test transform"
        assert t["enabled"] is True
        assert t["is_default"] is False

        fetched = get_transform(t["id"])
        assert fetched is not None
        assert fetched["sql"] == "SELECT 1 AS id"

    def test_get_transform_nonexistent(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import get_transform

        assert get_transform(9999) is None

    def test_list_transforms_filtered(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, list_transforms

        create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1",
        )
        create_transform(
            source_duckdb_schema="lunchmoney",
            source_duckdb_table="transactions",
            target_duckdb_schema="metrics",
            target_duckdb_table="spending",
            source_plugin="lunchmoney",
            sql="SELECT 2",
        )
        all_transforms = list_transforms()
        assert len(all_transforms) == 2

        garmin_only = list_transforms("garmin")
        assert len(garmin_only) == 1
        assert garmin_only[0]["source_plugin"] == "garmin"

    def test_update_transform(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, update_transform

        t = create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1",
        )
        updated = update_transform(t["id"], "SELECT 2 AS new_col")
        assert updated is not None
        assert updated["sql"] == "SELECT 2 AS new_col"
        assert updated["updated_at"] is not None

    def test_update_nonexistent_transform(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import update_transform

        # updating a non-existent ID returns None (no row matched)
        result = update_transform(9999, "SELECT 1")
        assert result is None

    def test_delete_transform(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, delete_transform, get_transform

        t = create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1",
        )
        assert delete_transform(t["id"]) is True
        assert get_transform(t["id"]) is None

    def test_delete_default_transform_blocked(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, delete_transform

        t = create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1",
            is_default=True,
        )
        assert delete_transform(t["id"]) is False

    def test_delete_nonexistent_transform(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import delete_transform

        assert delete_transform(9999) is False

    def test_set_transform_enabled(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import create_transform, set_transform_enabled

        t = create_transform(
            source_duckdb_schema="garmin",
            source_duckdb_table="activities",
            target_duckdb_schema="metrics",
            target_duckdb_table="daily_activities",
            source_plugin="garmin",
            sql="SELECT 1",
        )
        disabled = set_transform_enabled(t["id"], enabled=False)
        assert disabled is not None
        assert disabled["enabled"] is False
        assert disabled["status_changed_at"] is not None

        enabled = set_transform_enabled(t["id"], enabled=True)
        assert enabled is not None
        assert enabled["enabled"] is True

    def test_set_transform_enabled_nonexistent(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.transforms import set_transform_enabled

        assert set_transform_enabled(9999, enabled=True) is None


class TestUpdateSyncedAt:
    def test_update_synced_at_existing(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, update_synced_at, upsert_plugin_state

        upsert_plugin_state("pipe", "garmin", enabled=True)
        update_synced_at("pipe", "garmin")
        state = get_plugin_state("pipe", "garmin")
        assert state is not None
        assert state["synced_at"] is not None

    def test_update_synced_at_creates_missing(self, db_con: duckdb.DuckDBPyConnection, patch_db: None) -> None:
        from app.db import get_plugin_state, update_synced_at

        update_synced_at("pipe", "new-pipe")
        state = get_plugin_state("pipe", "new-pipe")
        assert state is not None
        assert state["synced_at"] is not None
