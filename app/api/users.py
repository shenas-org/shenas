"""Local user management API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

log = logging.getLogger(f"shenas.{__name__}")


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("")
def list_users() -> list[dict]:
    """List all local users (id + username, no password hashes)."""
    from app.local_users import LocalUser

    return LocalUser.list_all()


@router.post("/register")
def register_user(body: RegisterRequest) -> dict:
    """Create a new local user. Returns {id, username}."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    if not body.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if not body.password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    try:
        user = LocalUser.create(body.username.strip(), body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    token = LocalSession.set_user(user["id"])
    log.info("Registered local user: %s (id=%d)", user["username"], user["id"])
    return {"user": user, "token": token}


@router.post("/login")
def login_user(body: LoginRequest) -> dict:
    """Authenticate an existing local user. Returns {user, token}."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    user = LocalUser.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = LocalSession.set_user(user["id"])
    log.info("Local user logged in: %s (id=%d)", user["username"], user["id"])
    return {"user": user, "token": token}


@router.post("/logout")
def logout_user() -> dict:
    """Clear the active local session."""
    from app.local_sessions import LocalSession

    LocalSession.clear()
    return {"ok": True}


@router.get("/current")
def current_user(request: Request) -> dict:
    """Return the currently logged-in local user, or 401 if none."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="No active session")

    from app.local_users import LocalUser

    user = LocalUser.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session user not found")

    return {"user": user}
