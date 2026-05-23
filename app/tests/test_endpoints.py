"""Tests for server.py SSE streaming, remote auth, and SPA fallback."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

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
    def test_login_returns_authorization_url_when_configured(self, client: TestClient) -> None:
        """When KANIDM_URL is set, /api/auth/login returns an authorization URL and state."""
        with patch("app.main.KANIDM_URL", "https://auth.shenas.net"):
            resp = client.get("/api/auth/login")
        assert resp.status_code == 200
        body = resp.json()
        assert body["authorization_url"].startswith("https://auth.shenas.net/ui/oauth2?")
        assert "response_type=code" in body["authorization_url"]
        assert "code_challenge_method=S256" in body["authorization_url"]
        assert body["state"]

    def test_login_503_when_kanidm_not_configured(self, client: TestClient) -> None:
        with patch("app.main.KANIDM_URL", ""):
            resp = client.get("/api/auth/login")
        assert resp.status_code == 503

    def test_status_pending(self, client: TestClient) -> None:
        from app.auth_kanidm import PendingAuth, pending_auth_store

        pending_auth_store.put("state-pending", PendingAuth(code_verifier="v", redirect_uri="http://localhost/callback"))
        resp = client.get("/api/auth/status", params={"state": "state-pending"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "pending"}

    def test_status_authorized(self, client: TestClient) -> None:
        from app.auth_kanidm import PendingAuth, pending_auth_store

        entry = PendingAuth(code_verifier="v", redirect_uri="http://localhost/callback")
        entry.status = "authorized"
        pending_auth_store.put("state-ok", entry)
        resp = client.get("/api/auth/status", params={"state": "state-ok"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "authorized"}

    def test_status_unknown_state(self, client: TestClient) -> None:
        resp = client.get("/api/auth/status", params={"state": "nope"})
        assert resp.status_code == 404
        assert resp.json() == {"status": "expired"}

    def test_callback_exchanges_code_and_stores_token(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        from app.auth_kanidm import PendingAuth, pending_auth_store

        test_con.execute("INSERT INTO shenas.local_users (id, username) VALUES (1, 'default')")
        pending_auth_store.put(
            "state-cb", PendingAuth(code_verifier="verifier", redirect_uri="http://localhost:7280/callback")
        )
        with patch("app.auth_kanidm.exchange_code", return_value={"access_token": "hdr.pld.sig"}):
            resp = client.get("/callback", params={"code": "abc", "state": "state-cb"})
        assert resp.status_code == 200
        assert "Signed in" in resp.text
        entry = pending_auth_store.get("state-cb")
        assert entry is not None
        assert entry.status == "authorized"

    def test_callback_no_local_users_returns_actionable_error(
        self, client: TestClient, test_con: duckdb.DuckDBPyConnection
    ) -> None:
        from app.auth_kanidm import PendingAuth, pending_auth_store

        test_con.execute("DELETE FROM shenas.local_users")
        pending_auth_store.put("state-no-user", PendingAuth(code_verifier="v", redirect_uri="http://localhost:7280/callback"))
        with patch("app.auth_kanidm.exchange_code", return_value={"access_token": "hdr.pld.sig"}):
            resp = client.get("/callback", params={"code": "abc", "state": "state-no-user"})
        assert resp.status_code == 200
        assert "no local user exists" in resp.text
        entry = pending_auth_store.get("state-no-user")
        assert entry is not None
        assert entry.status == "error"

    def test_callback_unknown_state(self, client: TestClient) -> None:
        resp = client.get("/callback", params={"code": "abc", "state": "no-such"})
        assert resp.status_code == 200
        assert "Sign-in failed" in resp.text or "expired" in resp.text

    def test_me_no_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["user"] is None

    def test_me_with_legacy_token(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        """Legacy opaque tokens (pre-Phase 4) trigger a re-auth prompt."""
        test_con.execute(
            "INSERT INTO shenas.local_users (id, username, remote_token) VALUES (0, 'default', 'tok')"
            " ON CONFLICT (id) DO UPDATE SET remote_token = 'tok'"
        )
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"] is None
        assert body.get("needs_reauth") is True

    def test_me_with_valid_jwt(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        """A valid JWT yields the signed-in user; identity claims come from userinfo."""
        test_con.execute(
            "INSERT INTO shenas.local_users (id, username, remote_token) VALUES (0, 'default', 'hdr.pld.sig')"
            " ON CONFLICT (id) DO UPDATE SET remote_token = 'hdr.pld.sig'"
        )
        claims = {"sub": "abc-123"}
        userinfo = {"email": "alex@shenas.net", "name": "Alex", "picture": "https://example.com/a.png"}
        with (
            patch("app.auth_kanidm.validate_kanidm_jwt", return_value=claims),
            patch("app.auth_kanidm.fetch_userinfo", return_value=userinfo),
        ):
            resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == "abc-123"
        assert body["user"]["email"] == "alex@shenas.net"
        assert body["user"]["name"] == "Alex"
        assert body["user"]["picture"] == "https://example.com/a.png"
        assert "server_url" in body

    def test_me_with_invalid_jwt(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        """A JWT that fails validation flags needs_reauth so the UI re-prompts."""
        test_con.execute(
            "INSERT INTO shenas.local_users (id, username, remote_token) VALUES (0, 'default', 'hdr.pld.sig')"
            " ON CONFLICT (id) DO UPDATE SET remote_token = 'hdr.pld.sig'"
        )
        with patch("app.auth_kanidm.validate_kanidm_jwt", return_value=None):
            resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"] is None
        assert body.get("needs_reauth") is True
