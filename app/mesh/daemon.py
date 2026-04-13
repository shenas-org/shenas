"""Mesh daemon -- orchestrates device registration, sync, and transport.

Runs as a background task in the shenas app server. On startup:
1. Ensures device identity exists
2. Registers with shenas.net (if authenticated)
3. Refreshes endpoints periodically
4. Syncs with peers via direct connection or server relay
"""

from __future__ import annotations

import asyncio
import logging
import os

from app.config import SHENAS_NET_API_URL
from app.local_users import LocalUser

log = logging.getLogger("shenas.mesh")

SYNC_INTERVAL = int(os.environ.get("SHENAS_MESH_SYNC_INTERVAL", "60"))


async def run_mesh_daemon() -> None:
    """Main mesh loop. Call from the app lifespan."""
    from app.mesh.identity import get_device_info, register_with_server
    from app.mesh.relay_sync import sync_with_peers
    from app.mesh.sync_log import ensure_sync_tables
    from app.mesh.transport import SyncListener, refresh_endpoints

    ensure_sync_tables()
    info = get_device_info()
    log.info("Mesh device: %s (%s)", info["device_name"], info["device_type"])

    # Start the P2P listener
    listener = SyncListener()
    listener_task = asyncio.create_task(listener.start())

    try:
        while True:
            token = LocalUser.get_remote_token()
            device_id = _get_server_device_id()

            if token and not device_id:
                # Register with server
                result = register_with_server(SHENAS_NET_API_URL, token)
                if result:
                    _store_server_device_id(result["id"])
                    device_id = result["id"]

            if not token and device_id:
                # Token cleared (logout) -- clear stale device_id
                _clear_server_device_id()

            if token and device_id:
                # Refresh endpoints
                await refresh_endpoints(SHENAS_NET_API_URL, device_id, token)

                # Sync via relay (and try direct connections)
                try:
                    result = sync_with_peers(SHENAS_NET_API_URL)
                    if result["pushed"] or result["pulled"]:
                        log.info(
                            "Sync: pushed %d, pulled %d",
                            result["pushed"],
                            result["pulled"],
                        )
                except Exception:
                    log.exception("Sync cycle failed")

            await asyncio.sleep(SYNC_INTERVAL)
    finally:
        listener.stop()
        listener_task.cancel()


def _get_server_device_id() -> str | None:
    from app.database import cursor

    try:
        with cursor() as cur:
            row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'server_device_id'").fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _store_server_device_id(device_id: str) -> None:
    from app.database import cursor

    with cursor() as cur:
        cur.execute(
            "INSERT INTO shenas_system.device_identity (key, value) VALUES ('server_device_id', ?)"
            " ON CONFLICT (key) DO UPDATE SET value = ?",
            [device_id, device_id],
        )


def _clear_server_device_id() -> None:
    from app.database import cursor

    try:
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.device_identity WHERE key = 'server_device_id'")
    except Exception:
        pass
