"""Tests for Source.run_sync_stream -- threaded queue draining + per-resource progress."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from shenas_sources.core.source import Source


class _FakeSource(Source):
    name = "fake"

    def __init__(self, sync_impl: Any) -> None:
        # Skip the real Source.__init__ which initializes auth/config stores --
        # has_auth/is_authenticated are properties that resolve to False/True
        # because we don't override Source.Auth.
        self._sync_impl = sync_impl

    # Required abstract methods on Source -- stub them out.
    def build_client(self) -> Any:
        return None

    def resources(self, _client: Any) -> list[Any]:
        return []

    def acquire_sync_lock(self) -> bool:
        return True

    def release_sync_lock(self) -> None:
        pass

    def sync(self, *, full_refresh: bool = False, on_progress: Any = None, **_: Any) -> None:
        self._sync_impl(on_progress)


class TestRunSyncStreamProgress:
    def test_yields_starting_then_progress_then_complete(self) -> None:
        def _sync_impl(on_progress: Any) -> None:
            on_progress("fetch_start", "Fetching (1/2): r1")
            on_progress("fetch_done", "r1")
            on_progress("flush", "r1")
            on_progress("fetch_start", "Fetching (2/2): r2")
            on_progress("fetch_done", "r2")
            on_progress("flush", "r2")

        source = _FakeSource(_sync_impl)
        events = list(source.run_sync_stream())

        assert events[0] == ("progress", "starting sync")
        assert events[-1] == ("complete", "Sync complete: fake")
        # All per-resource progress events should be in between, in order.
        progress_messages = [m for e, m in events[1:-1]]
        assert "Fetching (1/2): r1" in progress_messages
        assert "Fetching (2/2): r2" in progress_messages
        assert progress_messages.index("Fetching (1/2): r1") < progress_messages.index("Fetching (2/2): r2")

    def test_error_path_yields_error_event(self) -> None:
        def _sync_impl(on_progress: Any) -> None:
            on_progress("fetch_start", "Fetching (1/1): r1")
            msg = "API rate limit"
            raise RuntimeError(msg)

        source = _FakeSource(_sync_impl)
        events = list(source.run_sync_stream())
        kinds = [e for e, _ in events]
        assert "error" in kinds
        error_messages = [m for e, m in events if e == "error"]
        assert any("API rate limit" in m for m in error_messages)
        # No "complete" event after an error.
        assert "complete" not in kinds

    def test_no_progress_events_still_completes(self) -> None:
        def _sync_impl(_on_progress: Any) -> None:
            return None

        source = _FakeSource(_sync_impl)
        events = list(source.run_sync_stream())
        assert events[0] == ("progress", "starting sync")
        assert events[-1] == ("complete", "Sync complete: fake")

    def test_unauthenticated_short_circuits(self) -> None:
        def _sync_impl(_on_progress: Any) -> None:
            msg = "should not be called"
            raise AssertionError(msg)

        # Subclass overriding the has_auth / is_authenticated properties.
        class _UnauthSource(_FakeSource):
            has_auth = True  # type: ignore[assignment]
            is_authenticated = False  # type: ignore[assignment]

        source = _UnauthSource(_sync_impl)
        events = list(source.run_sync_stream())
        assert events[0] == ("progress", "starting sync")
        assert events[1][0] == "error"
        assert "Not authenticated" in events[1][1]

    def test_complete_message_uses_display_name(self) -> None:
        class _NamedSource(_FakeSource):
            display_name = "Garmin Connect"

        def _sync_impl(_on_progress: Any) -> None:
            return None

        source = _NamedSource(_sync_impl)
        events = list(source.run_sync_stream())
        assert events[-1] == ("complete", "Sync complete: Garmin Connect")

    def test_carries_job_id_into_worker_thread(self) -> None:
        from app.jobs import bind_job_id, get_job_id

        seen: list[str | None] = []

        def _sync_impl(_on_progress: Any) -> None:
            seen.append(get_job_id())

        source = _FakeSource(_sync_impl)
        with bind_job_id("parent-job"), patch.object(source, "_log_sync_event"), patch.object(source, "_mark_synced"):
            list(source.run_sync_stream())

        assert seen == ["parent-job"]
