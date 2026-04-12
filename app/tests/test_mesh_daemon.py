"""Tests for app.mesh.daemon -- token/device-id helpers + run loop scaffolding."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.mesh import daemon


def _drive(coro: Any) -> Any:
    """Drive an async coroutine that does no real awaits to completion."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    return None


class TestGetRemoteToken:
    def test_returns_value_when_present(self, patch_db: None) -> None:
        from app.db import current_user_id, cursor
        from app.local_users import LocalUser

        with cursor() as cur:
            cur.execute(
                "INSERT INTO shenas_system.local_users (id, username, password_hash, key_salt, remote_token) "
                "VALUES (1, 'test', '', '', 'tok-123')"
            )
        token = current_user_id.set(1)
        try:
            assert LocalUser.get_remote_token() == "tok-123"
        finally:
            current_user_id.reset(token)

    def test_returns_none_when_no_user(self, patch_db: None) -> None:
        from app.local_users import LocalUser

        assert LocalUser.get_remote_token() is None


class TestServerDeviceId:
    def test_returns_none_when_unset(self, patch_db: None) -> None:
        assert daemon._get_server_device_id() is None

    def test_store_then_get(self, patch_db: None) -> None:
        from app.db import cursor

        with cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS shenas_system.device_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        daemon._store_server_device_id("server-dev-1")
        assert daemon._get_server_device_id() == "server-dev-1"

    def test_store_overwrites_existing(self, patch_db: None) -> None:
        from app.db import cursor

        with cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS shenas_system.device_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        daemon._store_server_device_id("first")
        daemon._store_server_device_id("second")
        assert daemon._get_server_device_id() == "second"


class TestRunMeshDaemon:
    """Drive a single iteration of the mesh loop with everything mocked."""

    def test_one_iteration_unauthenticated(self, patch_db: None) -> None:
        # No token -> skip register/refresh/sync, then sleep raises CancelledError
        listener = MagicMock()
        listener.start = AsyncMock()
        listener.stop = MagicMock()

        async def _no_sleep(_: float) -> None:
            raise asyncio.CancelledError

        with (
            patch("app.mesh.identity.get_device_info", return_value={"device_name": "x", "device_type": "desktop"}),
            patch("app.mesh.identity.register_with_server") as mock_reg,
            patch("app.mesh.relay_sync.sync_with_peers") as mock_sync,
            patch("app.mesh.transport.SyncListener", return_value=listener),
            patch("app.mesh.transport.refresh_endpoints", new=AsyncMock()) as mock_refresh,
            patch("app.mesh.sync_log.ensure_sync_tables") as mock_tables,
            patch("app.local_users.LocalUser.get_remote_token", return_value=None),
            patch("app.mesh.daemon._get_server_device_id", return_value=None),
            patch("asyncio.create_task", return_value=MagicMock()),
            patch("asyncio.sleep", side_effect=_no_sleep),
            contextlib.suppress(asyncio.CancelledError),
        ):
            _drive(daemon.run_mesh_daemon())
        mock_tables.assert_called_once()
        mock_reg.assert_not_called()
        mock_refresh.assert_not_called()
        mock_sync.assert_not_called()

    def test_one_iteration_authenticated_registers_and_syncs(self, patch_db: None) -> None:
        listener = MagicMock()
        listener.start = AsyncMock()
        listener.stop = MagicMock()

        async def _no_sleep(_: float) -> None:
            raise asyncio.CancelledError

        with (
            patch("app.mesh.identity.get_device_info", return_value={"device_name": "x", "device_type": "desktop"}),
            patch("app.mesh.identity.register_with_server", return_value={"id": "srv-dev"}) as mock_reg,
            patch("app.mesh.relay_sync.sync_with_peers", return_value={"pushed": 2, "pulled": 3}) as mock_sync,
            patch("app.mesh.transport.SyncListener", return_value=listener),
            patch("app.mesh.transport.refresh_endpoints", new=AsyncMock()) as mock_refresh,
            patch("app.mesh.sync_log.ensure_sync_tables"),
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.daemon._get_server_device_id", side_effect=[None, "srv-dev"]),
            patch("app.mesh.daemon._store_server_device_id") as mock_store,
            patch("asyncio.create_task", return_value=MagicMock()),
            patch("asyncio.sleep", side_effect=_no_sleep),
            contextlib.suppress(asyncio.CancelledError),
        ):
            _drive(daemon.run_mesh_daemon())
        mock_reg.assert_called_once()
        mock_store.assert_called_once_with("srv-dev")
        mock_refresh.assert_awaited_once()
        mock_sync.assert_called_once()

    def test_sync_exception_is_swallowed(self, patch_db: None) -> None:
        listener = MagicMock()
        listener.start = AsyncMock()
        listener.stop = MagicMock()

        async def _no_sleep(_: float) -> None:
            raise asyncio.CancelledError

        with (
            patch("app.mesh.identity.get_device_info", return_value={"device_name": "x", "device_type": "desktop"}),
            patch("app.mesh.identity.register_with_server"),
            patch("app.mesh.relay_sync.sync_with_peers", side_effect=RuntimeError("boom")),
            patch("app.mesh.transport.SyncListener", return_value=listener),
            patch("app.mesh.transport.refresh_endpoints", new=AsyncMock()),
            patch("app.mesh.sync_log.ensure_sync_tables"),
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.daemon._get_server_device_id", return_value="srv-dev"),
            patch("asyncio.create_task", return_value=MagicMock()),
            patch("asyncio.sleep", side_effect=_no_sleep),
            contextlib.suppress(asyncio.CancelledError),
        ):
            _drive(daemon.run_mesh_daemon())
        # No exception escapes -- the daemon swallowed the boom.
