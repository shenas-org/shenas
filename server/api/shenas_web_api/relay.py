"""Server relay -- fallback sync when P2P is unavailable.

Devices push encrypted sync events to the server, which stores them
temporarily for the target device to pull. The server only sees
ciphertext.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from shenas_web_api.auth import get_current_user
from shenas_web_api.db import get_conn

router = APIRouter(prefix="/relay")

_RELAY_TABLE = """\
CREATE TABLE IF NOT EXISTS relay_messages (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    from_device_id TEXT NOT NULL,
    to_device_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
)"""


class RelayMessage(BaseModel):
    payload: str  # encrypted sync events as base64 or JSON string


@router.post("/{device_id}")
async def send_relay(device_id: str, body: RelayMessage, request: Request) -> dict:
    """Send an encrypted message to another device via server relay."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_conn() as conn:
        conn.execute(_RELAY_TABLE)
        # Verify sender has a registered device
        sender = conn.execute(
            "SELECT id FROM devices WHERE user_id = %(uid)s LIMIT 1",
            {"uid": user["id"]},
        ).fetchone()
        if not sender:
            raise HTTPException(status_code=400, detail="No registered device")
        # Verify target device belongs to the same user
        target = conn.execute(
            "SELECT id FROM devices WHERE id = %(did)s AND user_id = %(uid)s",
            {"did": device_id, "uid": user["id"]},
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target device not found")
        conn.execute(
            "INSERT INTO relay_messages (from_device_id, to_device_id, payload) VALUES (%(from)s, %(to)s, %(payload)s)",
            {"from": sender["id"], "to": device_id, "payload": body.payload},
        )
    return {"ok": True}


@router.get("")
async def poll_relay(request: Request, device_id: str | None = None) -> list[dict]:
    """Poll for relayed messages. Consumes (deletes) messages after reading."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not device_id:
        raise HTTPException(status_code=400, detail="device_id query param required")

    with get_conn() as conn:
        conn.execute(_RELAY_TABLE)
        # Verify device belongs to this user
        device = conn.execute(
            "SELECT id FROM devices WHERE id = %(did)s AND user_id = %(uid)s",
            {"did": device_id, "uid": user["id"]},
        ).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        rows = conn.execute(
            "SELECT id, from_device_id, payload, created_at"
            " FROM relay_messages WHERE to_device_id = %(did)s"
            " ORDER BY created_at LIMIT 100",
            {"did": device_id},
        ).fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            conn.execute(
                "DELETE FROM relay_messages WHERE id = ANY(%(ids)s)",
                {"ids": ids},
            )
    return [dict(r) for r in rows]
