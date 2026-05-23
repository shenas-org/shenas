"""Shenas metrics server -- FastAPI app with plugin discovery."""

from __future__ import annotations

import asyncio as _asyncio
import os as _os
import pathlib as _pathlib
import sys as _sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

# In PyInstaller bundles, add the plugin venv's site-packages to sys.path
# so importlib.metadata.entry_points() discovers installed plugins.
# Must happen before any plugin imports.
if getattr(_sys, "_MEIPASS", None):
    _plugin_site = _pathlib.Path.home() / ".shenas" / "plugins" / "lib"
    for _p in _plugin_site.glob("python*/site-packages"):
        if str(_p) not in _sys.path:
            _sys.path.insert(0, str(_p))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import KANIDM_URL, SHENAS_NET_URL

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from shenas_themes.core import Theme


@asynccontextmanager
async def _lifespan(_application: FastAPI) -> AsyncIterator[None]:  # noqa: PLR0912, PLR0915
    from app.telemetry.dispatcher import set_loop

    set_loop(_asyncio.get_running_loop())

    # Attach any users who opted in to background sync via the keyring.
    try:
        from app.local_users import LocalUser

        LocalUser.attach_remembered()
    except Exception:
        pass

    # Ensure system tables exist early so the first page load doesn't pay the DDL cost.
    try:
        from app.plugin import PluginInstance

        PluginInstance.ensure()
    except Exception:
        pass

    # Pre-warm dataset ownership cache.
    try:
        from app.api.db import dataset_plugin_ownership

        dataset_plugin_ownership()
    except Exception:
        pass

    # Seed default transforms for all installed sources.
    try:
        import contextlib
        from importlib.metadata import entry_points

        from shenas_transformers.core import Transformer

        for cls in Transformer.load_all():
            plugin = cls()
            for ep in entry_points(group="shenas.sources"):
                with contextlib.suppress(Exception):
                    plugin.seed_defaults_for_source(ep.name)
    except Exception:
        pass

    # In dev mode, seed auth/config from data/dev_credentials.json
    try:
        from app.dev_credentials import is_dev_mode, seed_from_json

        if is_dev_mode():
            seeded = seed_from_json()
            if seeded:
                import logging as _log

                _log.getLogger("shenas").info("Seeded %d source(s) from dev_credentials.json", seeded)
    except Exception:
        pass

    # Start mesh daemon in background (device sync)
    mesh_task = None
    try:
        from app.mesh.daemon import run_mesh_daemon

        mesh_task = _asyncio.create_task(run_mesh_daemon())
    except Exception:
        pass  # mesh not configured yet

    # Start embedded sync scheduler (disabled in dev to avoid noisy syncs on reload)
    scheduler_task = None
    if _os.environ.get("SHENAS_DEV") != "1":
        try:
            from app.sync_scheduler import run_sync_scheduler

            interval = int(_os.environ.get("SHENAS_SYNC_INTERVAL", "60"))
            scheduler_task = _asyncio.create_task(run_sync_scheduler(interval))
        except Exception:
            pass

    yield

    if scheduler_task:
        scheduler_task.cancel()
    if mesh_task:
        mesh_task.cancel()


app = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None, openapi_url=None)

# Initialize OpenTelemetry (spans + logs exported to DuckDB)
_telemetry = __import__("app.telemetry.setup", fromlist=["init_telemetry"])
_telemetry.init_telemetry("shenas-server")

# Global env-based settings
app.state.frontend_name = _os.environ.get("SHENAS_FRONTEND", "default")
app.state.default_theme = _os.environ.get("SHENAS_DEFAULT_THEME", "default")


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Inject user_id into request.state from the X-Shenas-Session header."""
    request.state.user_id = 0  # default: single-user mode
    token = request.headers.get("X-Shenas-Session")
    if token:
        try:
            from app.local_sessions import LocalSession

            user_id = LocalSession.validate_token(token)
            if user_id is not None:
                request.state.user_id = user_id
        except Exception:
            pass
    return await call_next(request)


# Register API routes (includes GraphQL at /api/graphql)
app.include_router(api_router)


_headless = _os.environ.get("SHENAS_HEADLESS", "").lower() in ("1", "true")


# ---------------------------------------------------------------------------
# Static plugin mounting (skipped in headless mode)
# ---------------------------------------------------------------------------

if not _headless:

    def _mount_static(kind: str, url_prefix: str) -> None:
        """Mount static dirs for all plugins of a given kind."""
        from app.plugin import Plugin

        for plugin in Plugin.load_by_kind(kind):
            if plugin.static_dir.is_dir():  # ty: ignore[unresolved-attribute]
                app.mount(
                    f"/{url_prefix}/{plugin.name}",
                    StaticFiles(directory=str(plugin.static_dir)),  # ty: ignore[unresolved-attribute]
                    name=f"{url_prefix}-{plugin.name}",
                )

    # App-level static dirs
    _app_dir = _pathlib.Path(__file__).parent
    _artifacts_images = _app_dir.parent / "artifacts" / "oss" / "images"
    if _artifacts_images.is_dir():
        app.mount("/static/images", StaticFiles(directory=str(_artifacts_images)), name="images")
    app.mount("/static", StaticFiles(directory=str(_app_dir / "static")), name="static")
    _vendor_dir = _app_dir / "vendor" / "dist"
    if _vendor_dir.is_dir():
        app.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")

    # Plugin static dirs
    _mount_static("dashboard", "dashboards")
    _mount_static("frontend", "frontend")
    _mount_static("theme", "themes")


# Plugin icon endpoint (always available -- it's an API route)
@app.get("/api/plugins/{kind}/{name}/icon.svg")
async def plugin_icon(kind: str, name: str) -> Response:
    """Serve a plugin's icon.svg from its package directory."""
    from app.plugin import Plugin

    cls = Plugin.load_by_name_and_kind(name, kind.rstrip("s"))
    if cls:
        path = cls().icon_path
        if path:
            return Response(content=path.read_text(), media_type="image/svg+xml")
    return JSONResponse(status_code=404, content={"detail": "Icon not found"})


# ---------------------------------------------------------------------------
# Theme + frontend resolution
# ---------------------------------------------------------------------------


def _get_active_theme() -> type[Theme] | None:
    """Find the one explicitly enabled theme. Falls back to --default-theme."""
    from shenas_themes.core import Theme

    themes = Theme.load_all()
    try:
        from app.plugin import PluginInstance

        for t in themes:
            inst = PluginInstance.find("theme", t.name)
            if inst and inst.enabled:
                return t
    except Exception:
        pass
    fallback = getattr(app.state, "default_theme", "default")
    for t in themes:
        if t.name == fallback:
            return t
    return themes[0] if themes else None


def _serve_frontend_html() -> HTMLResponse:
    """Read and serve the active frontend plugin's HTML from disk, or a fallback."""
    from shenas_frontends.core import Frontend

    frontends = Frontend.load_all()
    frontend_name = app.state.frontend_name
    try:
        from app.plugin import PluginInstance

        for fe in frontends:
            inst = PluginInstance.find("frontend", fe.name)
            if inst and inst.enabled:
                frontend_name = fe.name
                break
    except Exception:
        pass
    fe = next((f for f in frontends if f.name == frontend_name), None)
    if fe:
        html_file = fe.static_dir / fe.html
        if html_file.exists():
            content = html_file.read_text()
            theme = _get_active_theme()
            if theme:
                css_link = f'<link rel="stylesheet" href="/themes/{theme.name}/{theme.css}" data-shenas-theme>'
                content = content.replace("</head>", f"  {css_link}\n  </head>")
            return HTMLResponse(content=content)
    return HTMLResponse(content=_FALLBACK_HTML.format(frontend_name=frontend_name))


_FALLBACK_HTML = """\
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>shenas</title>
  <style>body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #222; }}</style>
  </head>
  <body>
    <h1>shenas</h1>
    <p>Frontend plugin <code>{frontend_name}</code> is not installed.</p>
    <p>Install it with: <code>shenasctl frontend add {frontend_name}</code></p>
    <p>Or start with a different frontend: <code>shenas --frontend other-name</code></p>
    <h2>API</h2>
    <ul>
      <li><a href="/api/health">GET /api/health</a></li>
      <li><a href="/api/tables">GET /api/tables</a></li>
      <li><a href="/api/db/status">GET /api/db/status</a></li>
      <li><a href="/api/graphql">POST /api/graphql</a></li>
    </ul>
  </body>
</html>"""


# ---------------------------------------------------------------------------
# SSE streaming endpoints (stay as REST -- not suitable for GraphQL)
# ---------------------------------------------------------------------------


@app.get("/api/stream/logs")
async def stream_logs() -> StreamingResponse:
    """SSE stream of new log entries."""
    from app.telemetry.dispatcher import subscribe, unsubscribe

    q = subscribe()

    async def _generate() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    event = await _asyncio.wait_for(q.get(), timeout=30)
                    if event.get("type") == "log":
                        import json

                        yield f"data: {json.dumps(event['data'])}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.get("/api/stream/spans")
async def stream_spans() -> StreamingResponse:
    """SSE stream of new span entries."""
    from app.telemetry.dispatcher import subscribe, unsubscribe

    q = subscribe()

    async def _generate() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    event = await _asyncio.wait_for(q.get(), timeout=30)
                    if event.get("type") == "span":
                        import json

                        yield f"data: {json.dumps(event['data'])}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(_generate(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Remote auth — Kanidm OAuth2 authorization-code + PKCE (RFC 8252 native app)
# ---------------------------------------------------------------------------


@app.get("/api/auth/login")
def remote_login() -> JSONResponse:
    """Start the Kanidm auth-code flow.

    Returns the authorization URL the UI should open in the system browser, and
    a `state` value the UI polls via /api/auth/status until the loopback
    callback completes.
    """
    if not KANIDM_URL:
        return JSONResponse(content={"error": "KANIDM_URL is not configured"}, status_code=503)
    from app.auth_kanidm import build_authorization_url

    try:
        url, state = build_authorization_url()
        return JSONResponse(content={"authorization_url": url, "state": state})
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)


@app.get("/api/auth/status")
def remote_auth_status(state: str) -> JSONResponse:
    """Return the status of an in-flight auth-code flow keyed by `state`."""
    from app.auth_kanidm import pending_auth_store

    entry = pending_auth_store.get(state)
    if entry is None:
        return JSONResponse(content={"status": "expired"}, status_code=404)
    body: dict[str, str] = {"status": entry.status}
    if entry.error:
        body["error"] = entry.error
    return JSONResponse(content=body)


@app.get("/callback")
def remote_callback(request: Request) -> HTMLResponse:
    """Loopback redirect target for the Kanidm auth-code flow.

    Exchanges the code for an access token and stores it on the current local
    user. Returns a small HTML page the user can close.
    """
    from app.auth_kanidm import exchange_code, pending_auth_store
    from app.local_users import LocalUser

    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    error = request.query_params.get("error", "")

    entry = pending_auth_store.get(state) if state else None
    if entry is None:
        return _render_callback_page(ok=False, message="Sign-in session expired or unknown state.")
    if error:
        entry.status = "error"
        entry.error = error
        return _render_callback_page(ok=False, message=f"Sign-in failed: {error}")
    if not code:
        entry.status = "error"
        entry.error = "missing authorization code"
        return _render_callback_page(ok=False, message="Sign-in failed: missing authorization code.")

    try:
        token = exchange_code(code, entry.code_verifier, entry.redirect_uri)
    except Exception as exc:
        entry.status = "error"
        entry.error = str(exc)
        return _render_callback_page(ok=False, message=f"Sign-in failed: {exc}")

    user_id = _resolve_signin_user_id(request)
    if user_id is None:
        entry.status = "error"
        entry.error = "no local user to attach the sign-in to"
        return _render_callback_page(
            ok=False,
            message="Sign-in succeeded with shenas.net but no local user exists to attach it to. Create a local user first.",
        )
    LocalUser.set_remote_token(user_id, token["access_token"])
    entry.status = "authorized"
    entry.access_token = token["access_token"]
    return _render_callback_page(ok=True, message="Sign-in complete. You can close this tab.")


def _resolve_signin_user_id(request: Request) -> int | None:
    """Pick the local user to attach the Kanidm token to.

    1. Honor the X-Shenas-Session-derived `request.state.user_id` if it points
       at a real row.
    2. Otherwise (single-user-mode default of 0, or stale id with no row),
       fall back to the lowest registered user id -- the common case where the
       desktop app has exactly one local user.
    Returns None if there are zero registered users.
    """
    from app.local_users import LocalUser

    candidate = getattr(request.state, "user_id", 0) or 0
    if candidate and LocalUser.find(candidate):
        return candidate
    rows = sorted(LocalUser.list_all(), key=lambda u: u["id"])
    return rows[0]["id"] if rows else None


def _render_callback_page(ok: bool, message: str) -> HTMLResponse:
    color = "#2e7d32" if ok else "#c62828"
    return HTMLResponse(
        f"""<!doctype html>
<html><head><meta charset="utf-8"><title>shenas sign-in</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #faf8f5; color: #2c2c28;
          display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
  .card {{ background: #fff; padding: 2rem 2.5rem; border-radius: 10px;
           box-shadow: 0 8px 32px rgba(0,0,0,0.12); max-width: 420px; text-align: center; }}
  h1 {{ font-size: 1.1rem; color: {color}; margin: 0 0 0.75rem; }}
  p {{ margin: 0; color: #5a5850; line-height: 1.45; font-size: 0.95rem; }}
</style></head>
<body><div class="card"><h1>{"Signed in" if ok else "Sign-in failed"}</h1><p>{message}</p></div>
<script>setTimeout(() => window.close(), 1500);</script>
</body></html>"""
    )


@app.post("/api/auth/logout")
def remote_logout() -> JSONResponse:
    """Clear the stored Kanidm token."""
    from app.database import current_user_id
    from app.local_users import LocalUser

    user_id = current_user_id.get()
    user = LocalUser.find(user_id)
    if user:
        user.remote_token = None
        user.save()
    return JSONResponse(content={"ok": True})


@app.get("/api/auth/source/{name}/callback")
def source_auth_callback(name: str, request: Request) -> RedirectResponse:
    """OAuth callback for source plugin authentication."""
    from shenas_sources.core.source import Source

    code = request.query_params.get("code", "")
    state = request.query_params.get("state")
    try:
        cls = Source.load_by_name(name)
        if not cls:
            return RedirectResponse(url=f"/settings/source/{name}?auth=error&message=Source+not+found")
        source = cls()
        source.complete_oauth(code=code, state=state)
        return RedirectResponse(url=f"/settings/source/{name}?auth=success")
    except Exception as exc:
        import urllib.parse

        msg = urllib.parse.quote(str(exc))
        return RedirectResponse(url=f"/settings/source/{name}?auth=error&message={msg}")


@app.get("/api/auth/me")
def remote_me() -> dict:
    """Validate the stored Kanidm JWT locally and return the signed-in user.

    The desktop app trusts Kanidm directly (signature + expiry) instead of
    round-tripping through shenas.ai -- each Kanidm OAuth2 client signs with
    its own key, and shenas.ai only knows the web client's JWKS. Legacy opaque
    session tokens trigger a re-auth prompt.
    """
    from app.auth_kanidm import fetch_userinfo, is_legacy_token, validate_kanidm_jwt
    from app.local_users import LocalUser

    token = LocalUser.get_remote_token()
    if not token:
        return {"user": None, "server_url": SHENAS_NET_URL}
    if is_legacy_token(token):
        return {"user": None, "server_url": SHENAS_NET_URL, "needs_reauth": True}

    claims = validate_kanidm_jwt(token)
    if claims is None:
        return {"user": None, "server_url": SHENAS_NET_URL, "needs_reauth": True}

    userinfo = fetch_userinfo(token) or {}
    return {
        "user": {
            "id": claims.get("sub", ""),
            "email": userinfo.get("email", ""),
            "name": userinfo.get("name") or userinfo.get("preferred_username") or "",
            "picture": userinfo.get("picture", ""),
        },
        "server_url": SHENAS_NET_URL,
    }


# ---------------------------------------------------------------------------
# System settings endpoints
# ---------------------------------------------------------------------------


@app.get("/api/settings/system")
def get_system_settings() -> JSONResponse:
    """Return system-wide settings (e.g. multiuser_enabled)."""
    from app.system_settings import SystemSettings

    return JSONResponse(content=SystemSettings.read_row() or {"id": 1, "multiuser_enabled": False})


@app.put("/api/settings/system")
async def update_system_settings(request: Request) -> JSONResponse:
    """Update system-wide settings."""
    from app.system_settings import SystemSettings

    body = await request.json()
    multiuser_enabled = bool(body.get("multiuser_enabled", False))
    SystemSettings.write_row(multiuser_enabled=multiuser_enabled)
    return JSONResponse(content=SystemSettings.read_row() or {"id": 1, "multiuser_enabled": False})


# ---------------------------------------------------------------------------
# Dev credentials (dev mode only)
# ---------------------------------------------------------------------------


@app.post("/api/dev/export-credentials")
def export_dev_credentials() -> JSONResponse:
    """Export credentials, config, and entities to data/dev_credentials.json (dev mode only)."""
    from app.dev_credentials import export_current_state, is_dev_mode, save_dev_state

    if not is_dev_mode():
        raise HTTPException(status_code=403, detail="Only available in development mode")

    data = export_current_state()
    save_dev_state(data)
    entity_counts = {k: len(v) for k, v in data.get("entities", {}).items()}
    return JSONResponse(
        content={
            "ok": True,
            "sources": list(data.get("sources", {}).keys()),
            "entities": entity_counts,
        }
    )


# ---------------------------------------------------------------------------
# HTML routes (skipped in headless mode)
# ---------------------------------------------------------------------------

if not _headless:

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        """Serve the active frontend plugin as the app shell."""
        return _serve_frontend_html()

    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    def spa_fallback(path: str) -> HTMLResponse:  # noqa: ARG001
        """SPA fallback -- serve frontend HTML for any unmatched route."""
        return _serve_frontend_html()
