"""Relay sync -- push/pull sync events via the shenas.net server relay.

This is the fallback transport when P2P is unavailable. The server
only sees encrypted payloads.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.mesh.sync_log import (
    append_event,
    get_events_since,
    get_sync_cursor,
    set_sync_cursor,
)

log = logging.getLogger("shenas.mesh.relay")


def _get_remote_token() -> str | None:
    """Read the stored remote auth token."""
    from app.db import cursor

    try:
        with cursor() as cur:
            row = cur.execute("SELECT value FROM shenas_system.remote_auth WHERE key = 'token'").fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _get_device_id() -> str | None:
    """Read the local device's server-assigned ID."""
    from app.db import cursor

    try:
        with cursor() as cur:
            row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'server_device_id'").fetchone()
        return row[0] if row else None
    except Exception:
        return None


def push_to_peer(
    server_url: str,
    target_device_id: str,
    events: list[dict[str, Any]],
) -> bool:
    """Push sync events to a peer device via the server relay."""
    token = _get_remote_token()
    if not token:
        log.warning("No remote auth token, cannot push")
        return False

    payload = json.dumps(events)
    try:
        resp = httpx.post(
            f"{server_url}/api/relay/{target_device_id}",
            json={"payload": payload},
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=10,
        )
        if resp.status_code == 200:
            log.info("Pushed %d events to %s", len(events), target_device_id)
            return True
        log.warning("Push failed: %s", resp.text)
    except Exception:
        log.exception("Push failed")
    return False


def pull_from_relay(server_url: str) -> list[dict[str, Any]]:
    """Pull pending relay messages for this device."""
    token = _get_remote_token()
    device_id = _get_device_id()
    if not token or not device_id:
        return []

    try:
        resp = httpx.get(
            f"{server_url}/api/relay",
            params={"device_id": device_id},
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=10,
        )
        if resp.status_code == 200:
            messages = resp.json()
            log.info("Pulled %d relay messages", len(messages))
            return messages
    except Exception:
        log.exception("Pull failed")
    return []


def apply_remote_events(events_json: str) -> int:
    """Apply sync events received from a peer. Returns count applied."""
    events = json.loads(events_json)
    count = 0
    for event in events:
        # Skip events that originated from this device
        from app.mesh.sync_log import _get_device_id as get_local_id

        if event.get("device_id") == get_local_id():
            continue
        append_event(
            table_schema=event["table_schema"],
            table_name=event["table_name"],
            operation=event["operation"],
            row_key=event.get("row_key"),
            payload=event.get("payload"),
        )
        count += 1
    return count


def sync_with_peers(server_url: str) -> dict[str, int]:
    """Full relay sync cycle: push local events to peers, pull from relay."""
    token = _get_remote_token()
    device_id = _get_device_id()
    if not token or not device_id:
        return {"pushed": 0, "pulled": 0}

    # Discover peers
    try:
        resp = httpx.get(
            f"{server_url}/api/devices",
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=10,
        )
        peers = [d for d in resp.json() if d["id"] != device_id]
    except Exception:
        peers = []

    pushed = 0
    for peer in peers:
        cursor = get_sync_cursor(peer["id"])
        events = get_events_since(cursor)
        if events and push_to_peer(server_url, peer["id"], events):
            set_sync_cursor(peer["id"], events[-1]["event_id"])
            pushed += len(events)

    # Pull messages addressed to us
    pulled = 0
    messages = pull_from_relay(server_url)
    for msg in messages:
        count = apply_remote_events(msg["payload"])
        pulled += count

    return {"pushed": pushed, "pulled": pulled}
