"""User management REST endpoints."""

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


@router.get("")
def list_users() -> list[dict]:
    from app.local_users import LocalUser

    return LocalUser.list_all()


@router.post("/register")
def register_user(body: RegisterRequest) -> dict:
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    try:
        user = LocalUser.create(body.username, body.password)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = LocalSession.set_user(user["id"])
    return {"user": user, "token": token}


@router.post("/login")
def login_user(body: LoginRequest) -> dict:
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    user = LocalUser.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = LocalSession.set_user(user["id"])
    return {"user": user, "token": token}


@router.post("/logout")
def logout_user() -> dict:
    from app.local_sessions import LocalSession

    LocalSession.clear()
    return {"ok": True}


@router.get("/current")
def current_user() -> dict:
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    session = LocalSession.get_current()
    if not session or not session.get("user_id"):
        raise HTTPException(status_code=401, detail="No active session")
    user = LocalUser.get_by_id(session["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Session user not found")
    return {"user": user}
