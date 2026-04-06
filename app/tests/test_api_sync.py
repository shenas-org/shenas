"""Tests for the sync API endpoints with SSE streaming."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.server import app
from app.tests.conftest import parse_sse
from shenas_pipes.core.pipe import Pipe

client = TestClient(app)


class _FakePipe(Pipe):
    """Minimal Pipe subclass for testing."""

    name = "fake"
    display_name = "Fake"

    def __init__(self, sync_fn=None, *, pipe_name: str = "fake") -> None:
        # Skip real __init__ (DataclassStore) to avoid DB dependency
        self._sync_fn = sync_fn
        self.name = pipe_name

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
        pipe = _FakePipe(pipe_name="testpipe")
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

        pipe = _FakePipe(failing_sync, pipe_name="badpipe")
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
        pipe = _FakePipe(pipe_name="garmin")
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

        pipe = _FakePipe(sync_fn, pipe_name="garmin")
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

        pipe = _FakePipe(failing_sync, pipe_name="garmin")
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync/garmin")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Connection refused" in e["message"] for e in errors)

    def test_sync_pipe_lock_conflict(self) -> None:
        pipe = _FakePipe(pipe_name="garmin")
        pipe.acquire_sync_lock = lambda: False  # type: ignore[assignment]
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync/garmin")
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["detail"]


class TestSseEvent:
    def test_formats_correctly(self) -> None:
        import json

        from app.api.sync import _sse_event

        result = _sse_event("progress", {"pipe": "garmin", "message": "starting"})
        assert result.startswith("event: progress\n")
        assert "data:" in result
        data = json.loads(result.split("data: ")[1].strip())
        assert data == {"pipe": "garmin", "message": "starting"}


class TestInstalledPipeNames:
    def test_returns_enabled_pipes(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_pipe_names

        uv_output = json.dumps(
            [
                {"name": "shenas-pipe-garmin", "version": "0.1.0"},
                {"name": "shenas-pipe-core", "version": "0.1.0"},
                {"name": "unrelated-package", "version": "1.0"},
            ]
        )
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = False

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch("app.api.pipes._load_plugin", return_value=_FakeCls),
            patch("app.db.is_plugin_enabled", return_value=True),
        ):
            names = _installed_pipe_names()
        # garmin is included, core is excluded (name == "core")
        assert "garmin" in names
        assert "core" not in names
        assert "unrelated-package" not in names

    def test_returns_empty_on_uv_failure(self) -> None:
        import subprocess

        from app.api.sync import _installed_pipe_names

        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("app.api.sync.subprocess.run", return_value=mock_result):
            names = _installed_pipe_names()
        assert names == []

    def test_excludes_disabled_pipes(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_pipe_names

        uv_output = json.dumps([{"name": "shenas-pipe-garmin", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = False

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch("app.api.pipes._load_plugin", return_value=_FakeCls),
            patch("app.db.is_plugin_enabled", return_value=False),
        ):
            names = _installed_pipe_names()
        assert names == []

    def test_excludes_internal_pipes(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_pipe_names

        uv_output = json.dumps([{"name": "shenas-pipe-garmin", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = True

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch("app.api.pipes._load_plugin", return_value=_FakeCls),
            patch("app.db.is_plugin_enabled", return_value=True),
        ):
            names = _installed_pipe_names()
        assert names == []

    def test_skips_pipe_when_load_returns_none(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_pipe_names

        uv_output = json.dumps([{"name": "shenas-pipe-broken", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch("app.api.pipes._load_plugin", return_value=None),
        ):
            names = _installed_pipe_names()
        assert names == []


class TestSyncAllLockSkip:
    def test_sync_all_skips_locked_pipe(self) -> None:
        pipe = _FakePipe(pipe_name="locked")
        pipe.acquire_sync_lock = lambda: False  # type: ignore[assignment]
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["locked"]),
            patch("app.api.sync._load_pipe", return_value=pipe),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        progress = [e for e in events if e["_event"] == "progress"]
        assert any("skipping" in e.get("message", "") for e in progress)
        # Should still report overall completion
        complete = [e for e in events if e["_event"] == "complete"]
        assert any("all syncs complete" in e.get("message", "") for e in complete)

    def test_sync_all_reports_load_error(self) -> None:
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["broken"]),
            patch("app.api.sync._load_pipe", side_effect=ValueError("Pipe not found: broken")),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("broken" in e.get("pipe", "") for e in errors)
