"""Google OAuth routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer

from shenas_net_api.config import (
    BASE_URL,
    FRONTEND_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    SESSION_SECRET,
)
from shenas_net_api.db import get_conn

log = logging.getLogger("shenas-net-api.auth")

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
    # If redirect_uri is provided, store it for after OAuth completes (device/app login)
    redirect_uri = f"{BASE_URL}/api/auth/callback"
    app_redirect = request.query_params.get("redirect_uri", "")
    if app_redirect:
        request.session["app_redirect"] = app_redirect
    log.info("Login redirect, app_redirect=%s", app_redirect or "(website)")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    email = userinfo["email"]
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")
    google_id = userinfo["sub"]

    log.info("OAuth callback for %s", email)
    session_token = _create_session(email, name, picture, google_id)

    # If an app requested this login, redirect to it with the token
    app_redirect = request.session.pop("app_redirect", "")
    if app_redirect:
        sep = "&" if "?" in app_redirect else "?"
        return RedirectResponse(url=f"{app_redirect}{sep}token={session_token}", status_code=302)

    # Otherwise set a cookie for the website
    signed = _signer.dumps(session_token)
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        signed,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=BASE_URL.startswith("https"),
        samesite="lax",
        path="/",
    )
    return response


def _create_session(email: str, name: str, picture: str, google_id: str) -> str:
    """Create or update user and return a new session token."""
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
    return session_token


@router.get("/me")
async def me(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        return {"user": None}
    return {"user": user}


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        try:
            token = _signer.loads(cookie, max_age=SESSION_MAX_AGE)
            with get_conn() as conn:
                conn.execute("DELETE FROM sessions WHERE token = %(t)s", {"t": token})
        except Exception:
            pass
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


async def get_current_user(request: Request) -> dict | None:
    """Extract the current user from session cookie or Bearer token."""
    # Try Bearer token first (for app/CLI clients)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Fall back to signed session cookie (for website)
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
