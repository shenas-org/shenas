"""Worker deployment API -- create/list/delete headless workers from the dashboard."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shenas_net_api.auth import get_current_user, require_admin
from shenas_net_api.db import get_conn

router = APIRouter(prefix="/workers", tags=["workers"])

SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days


def _create_worker_token(user_id: str) -> str:
    """Create a long-lived session token for a worker to use as SHENAS_REMOTE_TOKEN."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (%(uid)s, %(tok)s, %(exp)s)",
            {"uid": user_id, "tok": token, "exp": expires_at},
        )
    return token


@router.post("")
async def create_worker(request: Request) -> JSONResponse:
    """Deploy a new headless worker in the cluster."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    body = await request.json()
    worker_name = body.get("name", "cloud-worker")

    # Create a session token for the worker to authenticate with shenas.net
    mesh_token = _create_worker_token(user["id"])

    # Store worker metadata
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO workers (user_id, name, deployment_name)
               VALUES (%(uid)s, %(name)s, '')
               RETURNING id""",
            {"uid": user["id"], "name": worker_name},
        ).fetchone()
        worker_id = row["id"]

        deployment_name = f"worker-{worker_id[:8]}"
        conn.execute(
            "UPDATE workers SET deployment_name = %(dn)s WHERE id = %(wid)s",
            {"dn": deployment_name, "wid": worker_id},
        )

    # Create K8s deployment
    from shenas_net_api.k8s import create_worker as k8s_create

    try:
        k8s_create(worker_id, mesh_token)
    except Exception as e:
        # Clean up DB entry on failure
        with get_conn() as conn:
            conn.execute("DELETE FROM workers WHERE id = %(wid)s", {"wid": worker_id})
        return JSONResponse(status_code=500, content={"error": f"Failed to create deployment: {e}"})

    return JSONResponse(
        status_code=201,
        content={"id": worker_id, "name": worker_name, "deployment_name": deployment_name, "status": "Pending"},
    )


@router.get("")
async def list_workers(request: Request) -> JSONResponse:
    """List the current user's workers with live status."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, deployment_name, created_at FROM workers WHERE user_id = %(uid)s ORDER BY created_at DESC",
            {"uid": user["id"]},
        ).fetchall()

    from shenas_net_api.k8s import get_worker_status

    workers = []
    for r in rows:
        status = get_worker_status(r["id"])
        workers.append(
            {
                "id": r["id"],
                "name": r["name"],
                "deployment_name": r["deployment_name"],
                "status": status,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )

    return JSONResponse(content=workers)


@router.get("/all")
async def list_all_workers(request: Request) -> JSONResponse:
    """List all workers across all users (admin only)."""
    await require_admin(request)

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT w.id, w.name, w.deployment_name, w.created_at,"
            " u.name AS owner_name, u.email AS owner_email"
            " FROM workers w JOIN users u ON w.user_id = u.id"
            " ORDER BY w.created_at DESC",
        ).fetchall()

    from shenas_net_api.k8s import get_worker_status

    workers = []
    for r in rows:
        status = get_worker_status(r["id"])
        workers.append(
            {
                "id": r["id"],
                "name": r["name"],
                "deployment_name": r["deployment_name"],
                "status": status,
                "owner_name": r["owner_name"],
                "owner_email": r["owner_email"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )

    return JSONResponse(content=workers)


@router.delete("/{worker_id}")
async def delete_worker(worker_id: str, request: Request) -> JSONResponse:
    """Delete a worker deployment and clean up secrets."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    # Verify ownership
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM workers WHERE id = %(wid)s AND user_id = %(uid)s",
            {"wid": worker_id, "uid": user["id"]},
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Worker not found"})

    # Delete K8s resources
    from shenas_net_api.k8s import delete_worker as k8s_delete

    try:
        k8s_delete(worker_id)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to delete: {e}"})

    # Delete DB record
    with get_conn() as conn:
        conn.execute("DELETE FROM workers WHERE id = %(wid)s", {"wid": worker_id})

    return JSONResponse(content={"ok": True})
