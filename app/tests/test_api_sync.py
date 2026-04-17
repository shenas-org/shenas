"""Tests for the sync API endpoints with SSE streaming."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import parse_sse
from shenas_sources.core.source import Source

client = TestClient(app)

_LOAD_BY_NAME = "shenas_sources.core.source.Source.load_by_name"
_LOAD_PLUGIN = "app.plugin.Plugin.load_by_name_and_kind"


class _FakeSource(Source):
    """Minimal Source subclass for testing."""

    name = "fake"
    display_name = "Fake"

    def __init__(self, sync_fn=None, *, source_name: str = "fake") -> None:
        # Skip real __init__ (TableStore) to avoid DB dependency
        self._sync_fn = sync_fn
        self.name = source_name

    def resources(self, client):
        return []

    def sync(self, *, full_refresh: bool = False, **_kwargs) -> None:
        if self._sync_fn:
            self._sync_fn(full_refresh=full_refresh)


class TestSyncAll:
    def test_sync_all_no_sources(self) -> None:
        with patch("app.api.sync._installed_source_names", return_value=[]):
            resp = client.post("/api/sync")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        events = parse_sse(resp.text)
        assert any(e.get("message") == "all syncs complete" for e in events)

    def test_sync_all_with_source(self) -> None:
        source = _FakeSource(source_name="testsource")
        with (
            patch("app.api.sync._installed_source_names", return_value=["testsource"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        complete = [e for e in events if e["_event"] == "complete"]
        # The fake source has no resources so it emits no per-resource progress;
        # only the final complete event for the source is expected.
        assert any(e["source"] == "testsource" and "Sync complete" in e["message"] for e in complete)

    def test_sync_all_reports_failure(self) -> None:
        def failing_sync(*, full_refresh: bool = False) -> None:
            raise RuntimeError("Auth expired")

        source = _FakeSource(failing_sync, source_name="badsource")
        with (
            patch("app.api.sync._installed_source_names", return_value=["badsource"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Auth expired" in e["message"] for e in errors)


class TestSyncSource:
    def test_sync_single_source(self) -> None:
        source = _FakeSource(source_name="garmin")
        with (
            patch("app.api.sync._installed_source_names", return_value=["garmin"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync/garmin")

        assert resp.status_code == 200
        events = parse_sse(resp.text)
        assert any(e.get("source") == "garmin" and "Sync complete" in (e.get("message") or "") for e in events)

    def test_sync_source_not_found(self) -> None:
        with patch("app.api.sync._installed_source_names", return_value=[]):
            resp = client.post("/api/sync/nonexistent")
        assert resp.status_code == 404

    def test_sync_source_with_full_refresh(self) -> None:
        captured = {}

        def sync_fn(*, full_refresh: bool = False) -> None:
            captured["full_refresh"] = full_refresh

        source = _FakeSource(sync_fn, source_name="garmin")
        with (
            patch("app.api.sync._installed_source_names", return_value=["garmin"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync/garmin", json={"full_refresh": True})

        assert resp.status_code == 200
        assert captured["full_refresh"] is True

    def test_sync_source_error(self) -> None:
        def failing_sync(*, full_refresh: bool = False) -> None:
            raise RuntimeError("Connection refused")

        source = _FakeSource(failing_sync, source_name="garmin")
        with (
            patch("app.api.sync._installed_source_names", return_value=["garmin"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync/garmin")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Connection refused" in e["message"] for e in errors)

    def test_sync_source_lock_conflict(self) -> None:
        source = _FakeSource(source_name="garmin")
        source.acquire_sync_lock = lambda: False  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        with (
            patch("app.api.sync._installed_source_names", return_value=["garmin"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync/garmin")
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["detail"]


class TestSseEvent:
    def test_formats_correctly(self) -> None:
        import json

        from app.api.sync import _sse_event

        result = _sse_event("progress", {"source": "garmin", "message": "starting"})
        assert result.startswith("event: progress\n")
        assert "data:" in result
        data = json.loads(result.split("data: ")[1].strip())
        # Outside any bind_job_id context the payload is unchanged.
        assert data == {"source": "garmin", "message": "starting"}

    def test_injects_job_id_from_contextvar(self) -> None:
        import json

        from app.api.sync import _sse_event
        from app.jobs import bind_job_id

        with bind_job_id("test-job-1234"):
            result = _sse_event("progress", {"source": "garmin", "message": "starting"})
        data = json.loads(result.split("data: ")[1].strip())
        assert data["job_id"] == "test-job-1234"
        assert data["source"] == "garmin"

    def test_does_not_clobber_explicit_job_id(self) -> None:
        import json

        from app.api.sync import _sse_event
        from app.jobs import bind_job_id

        with bind_job_id("from-context"):
            result = _sse_event("progress", {"source": "garmin", "message": "x", "job_id": "explicit"})
        data = json.loads(result.split("data: ")[1].strip())
        assert data["job_id"] == "explicit"


class TestSseStreamCarriesJobId:
    def test_every_event_has_same_job_id(self) -> None:
        source = _FakeSource(source_name="garmin")
        with (
            patch("app.api.sync._installed_source_names", return_value=["garmin"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
        ):
            resp = client.post("/api/sync/garmin")
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        ids = {e.get("job_id") for e in events if "job_id" in e}
        # All events for one request share the same job_id and it's a 16-char hex.
        assert len(ids) == 1
        (jid,) = ids
        assert isinstance(jid, str)
        assert len(jid) == 16


class TestInstalledSourceNames:
    def test_returns_enabled_sources(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_source_names

        uv_output = json.dumps(
            [
                {"name": "shenas-source-garmin", "version": "0.1.0"},
                {"name": "shenas-source-core", "version": "0.1.0"},
                {"name": "unrelated-package", "version": "1.0"},
            ]
        )
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = False

        class _FakeInstance:
            enabled = True

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch(_LOAD_PLUGIN, return_value=_FakeCls),
            patch("app.plugin.PluginInstance.find", return_value=_FakeInstance()),
        ):
            names = _installed_source_names()
        # garmin is included, core is excluded (name == "core")
        assert "garmin" in names
        assert "core" not in names
        assert "unrelated-package" not in names

    def test_returns_empty_on_uv_failure(self) -> None:
        import subprocess

        from app.api.sync import _installed_source_names

        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("app.api.sync.subprocess.run", return_value=mock_result):
            names = _installed_source_names()
        assert names == []

    def test_excludes_disabled_sources(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_source_names

        uv_output = json.dumps([{"name": "shenas-source-garmin", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = False

        class _FakeInstance:
            enabled = False

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch(_LOAD_PLUGIN, return_value=_FakeCls),
            patch("app.plugin.PluginInstance.find", return_value=_FakeInstance()),
        ):
            names = _installed_source_names()
        assert names == []

    def test_excludes_internal_sources(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_source_names

        uv_output = json.dumps([{"name": "shenas-source-garmin", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        class _FakeCls:
            internal = True

            @property
            def enabled(self):
                return True

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch(_LOAD_PLUGIN, return_value=_FakeCls),
        ):
            names = _installed_source_names()
        assert names == []

    def test_skips_source_when_load_returns_none(self) -> None:
        import json
        import subprocess

        from app.api.sync import _installed_source_names

        uv_output = json.dumps([{"name": "shenas-source-broken", "version": "0.1.0"}])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=uv_output, stderr="")

        with (
            patch("app.api.sync.subprocess.run", return_value=mock_result),
            patch(_LOAD_PLUGIN, return_value=None),
        ):
            names = _installed_source_names()
        assert names == []


class TestSyncAllLockSkip:
    def test_sync_all_skips_locked_source(self) -> None:
        source = _FakeSource(source_name="locked")
        source.acquire_sync_lock = lambda: False  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        with (
            patch("app.api.sync._installed_source_names", return_value=["locked"]),
            patch(_LOAD_BY_NAME, return_value=MagicMock(return_value=source)),
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
            patch("app.api.sync._installed_source_names", return_value=["broken"]),
            patch(_LOAD_BY_NAME, side_effect=ValueError("Source not found: broken")),
        ):
            resp = client.post("/api/sync")

        events = parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("broken" in e.get("source", "") for e in errors)
