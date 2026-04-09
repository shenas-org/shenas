"""Local user management REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


@router.get("")
def list_users() -> list[dict]:
    """List all registered local users (id + username only, no hashes)."""
    from app.local_users import LocalUser

    return LocalUser.list_all()


@router.post("/register")
def register_user(req: RegisterRequest) -> dict:
    """Register a new local user and activate a session. Returns {id, username, token}."""
    if not req.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if not req.password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    from app.local_sessions import LocalSession
    from app.local_users import LocalUser
    from app.user_keys import derive_user_key

    try:
        user = LocalUser.create(req.username.strip(), req.password)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    user.attach(derive_user_key(req.password, user.key_salt))
    token = LocalSession.set_user(user.id)
    return {"id": user.id, "username": user.username, "token": token}


@router.post("/login")
def login_user(req: LoginRequest) -> dict:
    """Authenticate an existing local user and activate a session. Returns {id, username, token}."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser
    from app.user_keys import derive_user_key

    user = LocalUser.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    derived = derive_user_key(req.password, user.key_salt)
    user.attach(derived)
    if req.remember:
        from app.user_keys import remember_user_key

        remember_user_key(user.id, derived)
    token = LocalSession.set_user(user.id)
    return {"id": user.id, "username": user.username, "token": token}


@router.post("/logout")
def logout_user() -> dict:
    """Deselect the current user session."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    session = LocalSession.get_current()
    if session and session.get("user_id") is not None:
        user_id = int(session["user_id"])
        user = LocalUser.get_by_id(user_id)
        if user is not None:
            user.detach()
        from app.user_keys import forget_user_key

        forget_user_key(user_id)
    LocalSession.clear()
    return {"ok": True}


@router.get("/current")
def current_user() -> dict:
    """Return the currently active session user, or 401 if none."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    session = LocalSession.get_current()
    if not session or session.get("user_id") is None:
        raise HTTPException(status_code=401, detail="No active user session")

    user = LocalUser.get_by_id(int(session["user_id"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Session user not found")
    return {"user": {"id": user.id, "username": user.username}}
