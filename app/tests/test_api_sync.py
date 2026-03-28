"""Tests for the sync API endpoints with SSE streaming."""

import json
from unittest.mock import patch

import typer
from fastapi.testclient import TestClient

from app.server import app

client = TestClient(app)


def _parse_sse(text: str) -> list[dict]:
    """Parse SSE text into a list of {_event, ...data} dicts."""
    events = []
    event_type = "message"
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:].strip())
            data["_event"] = event_type
            events.append(data)
            event_type = "message"
    return events


def _make_pipe_app(sync_fn=None) -> typer.Typer:
    """Create a minimal pipe typer app with a sync command."""
    pipe_app = typer.Typer()

    if sync_fn is None:

        def sync_fn(
            start_date: str = typer.Option("30 days ago"),
            full_refresh: bool = typer.Option(False),
        ) -> None:
            pass

    pipe_app.command("sync")(sync_fn)
    return pipe_app


class TestSyncAll:
    def test_sync_all_no_pipes(self) -> None:
        with patch("app.api.sync._installed_pipe_names", return_value=[]):
            resp = client.post("/api/sync")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        events = _parse_sse(resp.text)
        assert any(e.get("message") == "all syncs complete" for e in events)

    def test_sync_all_with_pipe(self) -> None:
        pipe_app = _make_pipe_app()
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["testpipe"]),
            patch("app.api.sync._load_pipe_app", return_value=pipe_app),
        ):
            resp = client.post("/api/sync")

        events = _parse_sse(resp.text)
        progress = [e for e in events if e["_event"] == "progress"]
        complete = [e for e in events if e["_event"] == "complete"]
        assert any(e["pipe"] == "testpipe" for e in progress)
        assert any(e["pipe"] == "testpipe" and e["message"] == "done" for e in complete)

    def test_sync_all_reports_failure(self) -> None:
        def failing_sync(
            start_date: str = typer.Option("30 days ago"),
            full_refresh: bool = typer.Option(False),
        ) -> None:
            raise RuntimeError("Auth expired")

        pipe_app = _make_pipe_app(failing_sync)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["badpipe"]),
            patch("app.api.sync._load_pipe_app", return_value=pipe_app),
        ):
            resp = client.post("/api/sync")

        events = _parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Auth expired" in e["message"] for e in errors)


class TestSyncPipe:
    def test_sync_single_pipe(self) -> None:
        pipe_app = _make_pipe_app()
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe_app", return_value=pipe_app),
        ):
            resp = client.post("/api/sync/garmin")

        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        assert any(e.get("pipe") == "garmin" and e.get("message") == "done" for e in events)

    def test_sync_pipe_not_found(self) -> None:
        with patch("app.api.sync._installed_pipe_names", return_value=[]):
            resp = client.post("/api/sync/nonexistent")
        assert resp.status_code == 404

    def test_sync_pipe_with_params(self) -> None:
        captured = {}

        def sync_fn(
            start_date: str = typer.Option("30 days ago"),
            full_refresh: bool = typer.Option(False),
        ) -> None:
            captured["start_date"] = start_date
            captured["full_refresh"] = full_refresh

        pipe_app = _make_pipe_app(sync_fn)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe_app", return_value=pipe_app),
        ):
            resp = client.post("/api/sync/garmin", json={"start_date": "2026-01-01", "full_refresh": True})

        assert resp.status_code == 200
        assert captured["start_date"] == "2026-01-01"
        assert captured["full_refresh"] is True

    def test_sync_pipe_error(self) -> None:
        def failing_sync(
            start_date: str = typer.Option("30 days ago"),
            full_refresh: bool = typer.Option(False),
        ) -> None:
            raise RuntimeError("Connection refused")

        pipe_app = _make_pipe_app(failing_sync)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["garmin"]),
            patch("app.api.sync._load_pipe_app", return_value=pipe_app),
        ):
            resp = client.post("/api/sync/garmin")

        events = _parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("Connection refused" in e["message"] for e in errors)

    def test_sync_pipe_no_sync_command(self) -> None:
        empty_app = typer.Typer()
        empty_app.command("auth")(lambda: None)
        with (
            patch("app.api.sync._installed_pipe_names", return_value=["nosync"]),
            patch("app.api.sync._load_pipe_app", return_value=empty_app),
        ):
            resp = client.post("/api/sync/nosync")

        events = _parse_sse(resp.text)
        errors = [e for e in events if e["_event"] == "error"]
        assert any("no sync command found" in e["message"] for e in errors)
