"""Tests for app.mesh.sync_log -- append-only sync event log."""

from __future__ import annotations

from app.mesh import sync_log


class TestAppendAndFetch:
    def test_append_single_event_returns_id(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        eid = sync_log.append_event("datasets", "daily_vitals", "INSERT", row_key="2026-04-07")
        assert isinstance(eid, str)
        assert len(eid) == 32  # uuid4 hex

    def test_get_events_since_returns_all_initially(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        e1 = sync_log.append_event("datasets", "daily_vitals", "INSERT", row_key="r1")
        e2 = sync_log.append_event("datasets", "daily_vitals", "UPDATE", row_key="r2")
        rows = sync_log.get_events_since(None)
        ids = {r["event_id"] for r in rows}
        assert {e1, e2}.issubset(ids)
        for r in rows:
            assert "device_id" in r
            assert "table_schema" in r

    def test_get_events_since_filters_by_event_id(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        e1 = sync_log.append_event("datasets", "tbl", "INSERT", row_key="r1")
        # Force a 1ms gap so the second event has a strictly higher ts
        import time

        time.sleep(0.005)
        e2 = sync_log.append_event("datasets", "tbl", "INSERT", row_key="r2")
        rows = sync_log.get_events_since(e1)
        ids = {r["event_id"] for r in rows}
        assert e2 in ids
        assert e1 not in ids

    def test_get_events_since_unknown_id_falls_back_to_full(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        e1 = sync_log.append_event("datasets", "tbl", "INSERT", row_key="r1")
        rows = sync_log.get_events_since("nonexistent-id-12345")
        ids = {r["event_id"] for r in rows}
        assert e1 in ids

    def test_limit_is_respected(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        for i in range(5):
            sync_log.append_event("datasets", "tbl", "INSERT", row_key=f"r{i}")
        rows = sync_log.get_events_since(None, limit=3)
        assert len(rows) == 3


class TestSyncCursor:
    def test_get_returns_none_when_unset(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        assert sync_log.get_sync_cursor("peer-a") is None

    def test_set_then_get(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        sync_log.set_sync_cursor("peer-a", "event-123")
        assert sync_log.get_sync_cursor("peer-a") == "event-123"

    def test_set_overwrites(self, patch_db: None) -> None:
        sync_log.ensure_sync_tables()
        sync_log.set_sync_cursor("peer-a", "event-1")
        sync_log.set_sync_cursor("peer-a", "event-2")
        assert sync_log.get_sync_cursor("peer-a") == "event-2"


class TestDeviceId:
    def test_get_device_id_creates_then_reuses(self, patch_db: None) -> None:
        first = sync_log._get_device_id()
        second = sync_log._get_device_id()
        assert first == second
        assert len(first) == 16
