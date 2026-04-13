"""Device registry API -- register, discover, and manage devices."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from shenas_net_api.auth import get_current_user, require_admin
from shenas_net_api.db import get_conn

router = APIRouter(prefix="/devices")


class DeviceRegister(BaseModel):
    name: str
    device_type: str
    public_key: str


class EndpointUpdate(BaseModel):
    endpoints: list[dict[str, str | int]]


@router.post("")
async def register_device(body: DeviceRegister, request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO devices (user_id, name, device_type, public_key, last_seen)
               VALUES (%(uid)s, %(name)s, %(type)s, %(key)s, now())
               RETURNING id, name, device_type, public_key, last_seen, created_at""",
            {"uid": user["id"], "name": body.name, "type": body.device_type, "key": body.public_key},
        ).fetchone()
    return dict(row)


@router.get("")
async def list_devices(request: Request) -> list[dict]:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, device_type, public_key, last_seen, created_at"
            " FROM devices WHERE user_id = %(uid)s ORDER BY created_at",
            {"uid": user["id"]},
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/all")
async def list_all_devices(request: Request) -> list[dict]:
    """List all registered devices across all users (admin only)."""
    await require_admin(request)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.id, d.name, d.device_type, d.last_seen, d.created_at,"
            " u.name AS owner_name, u.email AS owner_email"
            " FROM devices d JOIN users u ON d.user_id = u.id"
            " ORDER BY d.last_seen DESC",
        ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/{device_id}")
async def remove_device(device_id: str, request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM devices WHERE id = %(did)s AND user_id = %(uid)s RETURNING id",
            {"did": device_id, "uid": user["id"]},
        ).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True}


@router.put("/{device_id}/endpoints")
async def update_endpoints(device_id: str, body: EndpointUpdate, request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn:
        device = conn.execute(
            "SELECT id FROM devices WHERE id = %(did)s AND user_id = %(uid)s",
            {"did": device_id, "uid": user["id"]},
        ).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        for ep in body.endpoints:
            conn.execute(
                """INSERT INTO device_endpoints (device_id, endpoint_type, address, priority, updated_at)
                   VALUES (%(did)s, %(type)s, %(addr)s, %(pri)s, now())
                   ON CONFLICT (device_id, endpoint_type, address)
                   DO UPDATE SET priority = EXCLUDED.priority, updated_at = now()""",
                {"did": device_id, "type": ep["type"], "addr": ep["address"], "pri": ep.get("priority", 0)},
            )
        # Remove stale endpoints not in the current update
        if body.endpoints:
            keep_types = [ep["type"] for ep in body.endpoints]
            keep_addrs = [ep["address"] for ep in body.endpoints]
            conn.execute(
                """DELETE FROM device_endpoints
                   WHERE device_id = %(did)s
                     AND NOT EXISTS (
                       SELECT 1 FROM unnest(%(types)s::text[], %(addrs)s::text[]) AS k(t, a)
                       WHERE k.t = endpoint_type AND k.a = address
                     )""",
                {"did": device_id, "types": keep_types, "addrs": keep_addrs},
            )
        else:
            conn.execute("DELETE FROM device_endpoints WHERE device_id = %(did)s", {"did": device_id})
        conn.execute("UPDATE devices SET last_seen = now() WHERE id = %(did)s", {"did": device_id})
    return {"ok": True}


@router.get("/{device_id}/endpoints")
async def get_endpoints(device_id: str, request: Request) -> list[dict]:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn:
        # Verify device belongs to this user
        device = conn.execute(
            "SELECT id FROM devices WHERE id = %(did)s AND user_id = %(uid)s",
            {"did": device_id, "uid": user["id"]},
        ).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        rows = conn.execute(
            "SELECT endpoint_type, address, priority, updated_at"
            " FROM device_endpoints WHERE device_id = %(did)s ORDER BY priority DESC",
            {"did": device_id},
        ).fetchall()
    return [dict(r) for r in rows]
