"""Google OAuth routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer

from shenas_web_api.config import (
    BASE_URL,
    FRONTEND_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    SESSION_SECRET,
)
from shenas_web_api.db import get_conn

router = APIRouter(prefix="/auth")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

_signer = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE = "shenas_session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    redirect_uri = f"{BASE_URL}/api/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    email = userinfo["email"]
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")
    google_id = userinfo["sub"]

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (email, name, picture, google_id)
               VALUES (%(email)s, %(name)s, %(picture)s, %(google_id)s)
               ON CONFLICT (google_id) DO UPDATE
               SET name = EXCLUDED.name, picture = EXCLUDED.picture, updated_at = now()
               RETURNING id""",
            {"email": email, "name": name, "picture": picture, "google_id": google_id},
        )
        user = conn.execute("SELECT id FROM users WHERE google_id = %(gid)s", {"gid": google_id}).fetchone()
        user_id = user["id"]

        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE)
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (%(uid)s, %(token)s, %(exp)s)",
            {"uid": user_id, "token": session_token, "exp": expires_at},
        )

    signed = _signer.dumps(session_token)
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        signed,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me")
async def me(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        return {"user": None}
    return {"user": user}


@router.post("/logout")
async def logout(request: Request) -> dict:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        try:
            token = _signer.loads(cookie, max_age=SESSION_MAX_AGE)
            with get_conn() as conn:
                conn.execute("DELETE FROM sessions WHERE token = %(t)s", {"t": token})
        except Exception:
            pass
    response = Response(content='{"ok": true}', media_type="application/json")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


async def get_current_user(request: Request) -> dict | None:
    """Extract the current user from the session cookie."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    try:
        token = _signer.loads(cookie, max_age=SESSION_MAX_AGE)
    except Exception:
        return None
    with get_conn() as conn:
        row = conn.execute(
            """SELECT u.id, u.email, u.name, u.picture
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = %(t)s AND s.expires_at > now()""",
            {"t": token},
        ).fetchone()
    return dict(row) if row else None
