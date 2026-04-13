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

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from shenas_themes.core import Theme


@asynccontextmanager
async def _lifespan(_application: FastAPI) -> AsyncIterator[None]:
    from app.telemetry.dispatcher import set_loop

    set_loop(_asyncio.get_running_loop())

    # Attach any users who opted in to background sync via the keyring.
    try:
        from app.local_users import LocalUser

        LocalUser.attach_remembered()
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

    # Start embedded sync scheduler
    scheduler_task = None
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
# Theme + UI resolution
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


def _serve_ui_html() -> HTMLResponse:
    """Read and serve the active UI plugin's HTML from disk, or a fallback."""
    from shenas_frontends.core import Frontend

    uis = Frontend.load_all()
    # Check for enabled frontend, fall back to CLI/env setting
    frontend_name = app.state.frontend_name
    try:
        from app.plugin import PluginInstance

        for u in uis:
            inst = PluginInstance.find("frontend", u.name)
            if inst and inst.enabled:
                frontend_name = u.name
                break
    except Exception:
        pass
    ui = next((u for u in uis if u.name == frontend_name), None)
    if ui:
        html_file = ui.static_dir / ui.html
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
    <p>UI plugin <code>{frontend_name}</code> is not installed.</p>
    <p>Install it with: <code>shenasctl frontend add {frontend_name}</code></p>
    <p>Or start with a different UI: <code>shenas --frontend other-name</code></p>
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
# Remote auth (shenas.net login from the local app)
# ---------------------------------------------------------------------------

SHENAS_NET_URL = _os.environ.get("SHENAS_NET_URL", "https://shenas.net")


@app.get("/api/auth/login")
def remote_login(request: Request) -> RedirectResponse:
    """Redirect to shenas.net OAuth, which will redirect back with a token."""
    callback = str(request.url_for("remote_callback"))
    return RedirectResponse(url=f"{SHENAS_NET_URL}/api/auth/login?redirect_uri={callback}")


@app.get("/api/auth/callback")
def remote_callback(token: str | None = None) -> HTMLResponse:
    """Receive the token from shenas.net after OAuth and store it."""
    if token:
        from app.database import cursor

        with cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS shenas_system.remote_auth (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO shenas_system.remote_auth (key, value) VALUES ('token', ?) "
                "ON CONFLICT (key) DO UPDATE SET value = ?",
                [token, token],
            )
    return HTMLResponse(
        content="""
        <html><body style="font-family:system-ui;text-align:center;padding:4rem">
        <h2>Signed in</h2>
        <p>You can close this tab and return to shenas.</p>
        <script>setTimeout(() => window.close(), 2000)</script>
        </body></html>
    """
    )


@app.get("/api/auth/me")
def remote_me() -> dict:
    """Check if locally stored remote token is valid."""
    import httpx

    try:
        from app.database import cursor

        with cursor() as cur:
            row = cur.execute("SELECT value FROM shenas_system.remote_auth WHERE key = 'token'").fetchone()
        if not row:
            return {"user": None}
        resp = httpx.get(
            f"{SHENAS_NET_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {row[0]}"},
            verify=False,
            timeout=5,
        )
        return resp.json()
    except Exception:
        return {"user": None}


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
    """Export all source auth/config to data/dev_credentials.json (dev mode only)."""
    from app.dev_credentials import export_current_credentials, is_dev_mode, save_dev_credentials

    if not is_dev_mode():
        raise HTTPException(status_code=403, detail="Only available in development mode")

    data = export_current_credentials()
    save_dev_credentials(data)
    return JSONResponse(content={"ok": True, "sources": list(data.keys())})


# ---------------------------------------------------------------------------
# HTML routes (skipped in headless mode)
# ---------------------------------------------------------------------------

if not _headless:

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        """Serve the active UI plugin as the app shell."""
        return _serve_ui_html()

    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    def spa_fallback(path: str) -> HTMLResponse:  # noqa: ARG001
        """SPA fallback -- serve UI HTML for any unmatched route."""
        return _serve_ui_html()
