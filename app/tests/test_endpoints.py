"""Tests for server.py SSE streaming, remote auth, and SPA fallback."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.main import app

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


@pytest.fixture
def test_con() -> Iterator[duckdb.DuckDBPyConnection]:
    import app.database
    import app.db

    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")

    @contextlib.contextmanager
    def _cursor(**_kwargs: object) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = con.cursor()
        cur.execute("USE db")
        try:
            yield cur
        finally:
            cur.close()

    class _StubDB:
        def cursor(self) -> contextlib.AbstractContextManager:
            return _cursor()

        def connect(self) -> duckdb.DuckDBPyConnection:
            return con

        def close(self) -> None:
            pass

    stub = _StubDB()
    saved = dict(app.db._resolvers)
    app.db._resolvers["shenas"] = lambda: stub  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    app.db._resolvers[None] = lambda: stub  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    app.database._ensure_system_tables(con)
    yield con
    app.db._resolvers.clear()
    app.db._resolvers.update(saved)
    con.close()


@pytest.fixture
def client(test_con: duckdb.DuckDBPyConnection) -> Iterator[TestClient]:
    return TestClient(app)  # ty: ignore[invalid-return-type]


class TestSSEGenerators:
    """Directly drive the SSE async generator coroutines (avoids TestClient/streaming complexity)."""

    def _drive(self, gen):
        """Pull yields from an async generator until it ends or raises."""
        out = []
        loop = asyncio.new_event_loop()
        try:
            while True:
                try:
                    chunk = loop.run_until_complete(gen.__anext__())
                    out.append(chunk)
                except (StopAsyncIteration, Exception):
                    break
        finally:
            loop.close()
        return out

    def _make_wait_for(self, events):
        it = iter(events)

        async def _wait_for(coro, timeout):  # noqa: ASYNC109
            with contextlib.suppress(Exception):
                coro.close()
            ev = next(it)  # raises StopIteration -> ends generator
            if isinstance(ev, BaseException):
                raise ev
            return ev

        return _wait_for

    def test_log_stream_yields_data_and_keepalive(self, client: TestClient) -> None:
        from app.main import stream_logs

        q: asyncio.Queue = asyncio.Queue()
        events = [
            {"type": "log", "data": {"body": "hello"}},
            {"type": "span", "data": {"name": "ignored"}},
            TimeoutError(),
        ]
        with (
            patch("app.telemetry.dispatcher.subscribe", return_value=q),
            patch("app.telemetry.dispatcher.unsubscribe"),
            patch("app.main._asyncio.wait_for", side_effect=self._make_wait_for(events)),
        ):
            loop = asyncio.new_event_loop()
            try:
                resp = loop.run_until_complete(stream_logs())
            finally:
                loop.close()
            chunks = self._drive(resp.body_iterator)
        joined = "".join(chunks)
        assert "hello" in joined
        assert "keepalive" in joined
        assert "ignored" not in joined

    def test_span_stream_yields_data_and_keepalive(self, client: TestClient) -> None:
        from app.main import stream_spans

        q: asyncio.Queue = asyncio.Queue()
        events = [
            {"type": "span", "data": {"name": "myspan"}},
            {"type": "log", "data": {"body": "ignored"}},
            TimeoutError(),
        ]
        with (
            patch("app.telemetry.dispatcher.subscribe", return_value=q),
            patch("app.telemetry.dispatcher.unsubscribe"),
            patch("app.main._asyncio.wait_for", side_effect=self._make_wait_for(events)),
        ):
            loop = asyncio.new_event_loop()
            try:
                resp = loop.run_until_complete(stream_spans())
            finally:
                loop.close()
            chunks = self._drive(resp.body_iterator)
        joined = "".join(chunks)
        assert "myspan" in joined
        assert "keepalive" in joined
        assert "ignored" not in joined


class TestRemoteAuth:
    def test_login_redirects(self, client: TestClient) -> None:
        resp = client.get("/api/auth/login", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "shenas" in resp.headers["location"].lower() or "redirect_uri" in resp.headers["location"]

    def test_callback_stores_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/callback?token=abc123", follow_redirects=False)
        assert resp.status_code == 307
        assert "/settings/profile" in resp.headers["location"]

    def test_callback_no_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/callback", follow_redirects=False)
        assert resp.status_code == 307

    def test_me_no_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json() == {"user": None}

    def test_me_with_token(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas.local_users (id, username, remote_token) VALUES (0, 'default', 'tok')"
            " ON CONFLICT (id) DO UPDATE SET remote_token = 'tok'"
        )

        fake_resp = MagicMock()
        fake_resp.json.return_value = {"user": {"id": 1, "name": "alex"}}
        with patch("httpx.get", return_value=fake_resp):
            resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"] == {"id": 1, "name": "alex"}
        assert "server_url" in body

    def test_me_handles_httpx_error(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas.local_users (id, username, remote_token) VALUES (0, 'default', 'tok')"
            " ON CONFLICT (id) DO UPDATE SET remote_token = 'tok'"
        )

        with patch("httpx.get", side_effect=Exception("network down")):
            resp = client.get("/api/auth/me")
        assert resp.json()["user"] is None
