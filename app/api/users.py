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


class UserResponse(BaseModel):
    id: int
    username: str


class AuthResponse(BaseModel):
    id: int
    username: str
    token: str


class OkResponse(BaseModel):
    ok: bool = True


class CurrentUserResponse(BaseModel):
    user: UserResponse


@router.get("")
def list_users() -> list[dict]:
    """List all registered local users (id + username only, no hashes)."""
    from app.local_users import LocalUser

    return LocalUser.list_all()


@router.post("/register")
def register_user(req: RegisterRequest) -> AuthResponse:
    """Register a new local user and activate a session."""
    if not req.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if not req.password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    try:
        user = LocalUser.create(req.username.strip(), req.password)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    user.attach(LocalUser.derive_key(req.password, user.key_salt))
    token = LocalSession.set_user(user.id)
    return AuthResponse(id=user.id, username=user.username, token=token)


@router.post("/login")
def login_user(req: LoginRequest) -> AuthResponse:
    """Authenticate an existing local user and activate a session."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    user = LocalUser.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    derived = LocalUser.derive_key(req.password, user.key_salt)
    user.attach(derived)
    if req.remember:
        LocalUser.remember_key(user.id, derived)
    token = LocalSession.set_user(user.id)
    return AuthResponse(id=user.id, username=user.username, token=token)


@router.post("/logout")
def logout_user() -> OkResponse:
    """Deselect the current user session."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    session = LocalSession.get_current()
    if session and session.get("user_id") is not None:
        user_id = int(session["user_id"])
        user = LocalUser.get_by_id(user_id)
        if user is not None:
            user.detach()
        LocalUser.forget_key(user_id)
    LocalSession.clear()
    return OkResponse()


@router.get("/current")
def current_user() -> CurrentUserResponse:
    """Return the currently active session user, or 401 if none."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser

    session = LocalSession.get_current()
    if not session or session.get("user_id") is None:
        raise HTTPException(status_code=401, detail="No active user session")

    user = LocalUser.get_by_id(int(session["user_id"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Session user not found")
    return CurrentUserResponse(user=UserResponse(id=user.id, username=user.username))
