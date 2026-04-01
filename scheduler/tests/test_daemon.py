"""Tests for the SyncDaemon background scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scheduler.client import ShenasServerError
from scheduler.daemon import SyncDaemon


def _make_daemon(mock_client: MagicMock | None = None) -> SyncDaemon:
    """Create a SyncDaemon with a mocked SchedulerClient."""
    with patch("scheduler.client.SchedulerClient", return_value=mock_client or MagicMock()):
        daemon = SyncDaemon(server_url="http://localhost:7280", check_interval=1)
    return daemon


class TestTick:
    def test_no_due_pipes(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.return_value = []
        daemon = _make_daemon(client)

        daemon._tick()

        client.get_sync_schedule.assert_called_once()
        client.sync_pipe.assert_not_called()

    def test_syncs_due_pipes(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.return_value = [
            {"name": "garmin", "sync_frequency": 60, "synced_at": None, "is_due": True},
            {"name": "lunchmoney", "sync_frequency": 120, "synced_at": None, "is_due": True},
        ]
        client.sync_pipe.return_value = iter([{"_event": "complete", "pipe": "test", "message": "done"}])
        daemon = _make_daemon(client)

        daemon._tick()

        assert client.sync_pipe.call_count == 2
        client.sync_pipe.assert_any_call("garmin")
        client.sync_pipe.assert_any_call("lunchmoney")

    def test_skips_not_due(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.return_value = [
            {"name": "garmin", "sync_frequency": 60, "synced_at": "2026-03-30 15:00:00", "is_due": False},
            {"name": "lunchmoney", "sync_frequency": 120, "synced_at": None, "is_due": True},
        ]
        client.sync_pipe.return_value = iter([{"_event": "complete", "pipe": "lunchmoney", "message": "done"}])
        daemon = _make_daemon(client)

        daemon._tick()

        client.sync_pipe.assert_called_once_with("lunchmoney")

    def test_server_unreachable(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.side_effect = ShenasServerError(0, "Cannot reach server")
        daemon = _make_daemon(client)

        daemon._tick()
        client.sync_pipe.assert_not_called()

    def test_unexpected_error_caught_by_run_loop(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.side_effect = RuntimeError("unexpected")
        daemon = _make_daemon(client)
        daemon._shutdown.set()

        with patch("scheduler.daemon.signal"):
            daemon.run()


class TestSyncPipe:
    def test_consumes_sse_events(self) -> None:
        client = MagicMock()
        client.sync_pipe.return_value = iter(
            [
                {"_event": "progress", "pipe": "garmin", "message": "starting sync"},
                {"_event": "complete", "pipe": "garmin", "message": "done"},
            ]
        )
        daemon = _make_daemon(client)

        daemon._sync_pipe("garmin")
        client.sync_pipe.assert_called_once_with("garmin")

    @pytest.mark.parametrize(
        ("exception",),
        [
            (ShenasServerError(409, "Sync already in progress"),),
            (ShenasServerError(500, "Internal error"),),
            (RuntimeError("connection reset"),),
        ],
        ids=["409-conflict", "server-error", "generic-exception"],
    )
    def test_error_does_not_raise(self, exception: Exception) -> None:
        client = MagicMock()
        client.sync_pipe.side_effect = exception
        daemon = _make_daemon(client)

        daemon._sync_pipe("garmin")


class TestShutdown:
    def test_shutdown_stops_loop(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.return_value = []
        daemon = _make_daemon(client)
        daemon._shutdown.set()

        with patch("scheduler.daemon.signal"):
            daemon.run()

    def test_shutdown_interrupts_tick(self) -> None:
        client = MagicMock()
        client.get_sync_schedule.return_value = [
            {"name": "garmin", "is_due": True},
            {"name": "lunchmoney", "is_due": True},
        ]

        def set_shutdown_on_first_sync(name: str):
            daemon._shutdown.set()
            return iter([{"_event": "complete", "message": "done"}])

        client.sync_pipe.side_effect = set_shutdown_on_first_sync
        daemon = _make_daemon(client)

        daemon._tick()

        assert client.sync_pipe.call_count == 1
