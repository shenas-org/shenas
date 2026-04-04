"""Tests for the sync API endpoints with SSE streaming."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.server import app
from app.tests.conftest import parse_sse
from shenas_plugins.core import Pipe

client = TestClient(app)


class _FakePipe(Pipe):
    """Minimal Pipe subclass for testing."""

    name = "fake"
    display_name = "Fake"

    def __init__(self, sync_fn=None) -> None:
        # Skip real __init__ (DataclassStore) to avoid DB dependency
        self._sync_fn = sync_fn

    def resources(self, client):
        return []

    def sync(self, *, full_refresh: bool = False, **_kwargs) -> None:
        if self._sync_fn:
            self._sync_fn(full_refresh=full_refresh)


class TestSyncAll:
    def test_sync_all_no_pipes(self) -> None:
        with patch("app.api.sync._installed_pipe_names", return_value=[]):
            resp = client.post("/api/sync")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        events = parse_sse(resp.text)
        assert any(e.get("message") == "all syncs complete" for e in events)

    def test_sync_all_with_pipe(self) -> None:
        pipe = _FakePipe()
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["testpipe"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        progress = [e for e in events if e["_event"] == "progress"]
        complete = [e for e in events if e["_event"] == "complete"]
        assert any(e["pipe"] == "testpipe" for e in progress)
        assert any(e["pipe"] == "testpipe" and e["message"] == "done" for e in complete)

    def test_sync_all_reports_failure(self) -> None:
        def failing_sync(*, full_refresh: bool = False) -> None:
            raise RuntimeError("Auth expired")

        pipe = _FakePipe(failing_sync)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["badpipe"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Auth expired" in e["message"] for e in errors)


class TestSyncPipe:
    def test_sync_single_pipe(self) -> None:
        pipe = _FakePipe()
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync/garmin")

        assert resp.status_code == 200
        events = parse_sse(resp.text)
        assert any(e.get("pipe") == "garmin" and e.get("message") == "done" for e in events)

    def test_sync_pipe_not_found(self) -> None:
        with patch("app.api.sync._installed_pipe_names", return_value=[]):
            resp = client.post("/api/sync/nonexistent")
        assert resp.status_code == 404

    def test_sync_pipe_with_full_refresh(self) -> None:
        captured = {}

        def sync_fn(*, full_refresh: bool = False) -> None:
            captured["full_refresh"] = full_refresh

        pipe = _FakePipe(sync_fn)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync/garmin", json={"full_refresh": True})

        assert resp.status_code == 200
        assert captured["full_refresh"] is True

    def test_sync_pipe_error(self) -> None:
        def failing_sync(*, full_refresh: bool = False) -> None:
            raise RuntimeError("Connection refused")

        pipe = _FakePipe(failing_sync)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync/garmin")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Connection refused" in e["message"] for e in errors)
