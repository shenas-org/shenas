"""Shenas metrics server -- FastAPI app with plugin discovery."""

from __future__ import annotations

import asyncio as _asyncio
import os as _os
import pathlib as _pathlib
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from shenas_themes.core import Theme


@asynccontextmanager
async def _lifespan(_application: FastAPI) -> AsyncIterator[None]:
    from app.telemetry.dispatcher import set_loop

    set_loop(_asyncio.get_running_loop())
    yield


app = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None, openapi_url=None)

# Initialize OpenTelemetry (spans + logs exported to DuckDB)
_telemetry = __import__("app.telemetry.setup", fromlist=["init_telemetry"])
_telemetry.init_telemetry("shenas-server")

# Global env-based settings
app.state.ui_name = _os.environ.get("SHENAS_UI", "default")
app.state.default_theme = _os.environ.get("SHENAS_DEFAULT_THEME", "default")

# Register API routes
app.include_router(api_router)

# GraphQL endpoint
app.include_router(__import__("app.graphql", fromlist=["graphql_app"]).graphql_app, prefix="/graphql")


# ---------------------------------------------------------------------------
# Static plugin mounting
# ---------------------------------------------------------------------------


def _mount_static(kind: str, url_prefix: str) -> None:
    """Mount static dirs for all plugins of a given kind."""
    from app.api.pipes import _load_static_plugins

    for plugin in _load_static_plugins(kind):
        if plugin.static_dir.is_dir():
            app.mount(
                f"/{url_prefix}/{plugin.name}",
                StaticFiles(directory=str(plugin.static_dir)),
                name=f"{url_prefix}-{plugin.name}",
            )


# App-level static dirs

_app_dir = _pathlib.Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_app_dir / "static")), name="static")
_vendor_dir = _app_dir / "vendor" / "dist"
if _vendor_dir.is_dir():
    app.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")

# Plugin static dirs
_mount_static("component", "components")
_mount_static("ui", "ui")
_mount_static("theme", "themes")


# ---------------------------------------------------------------------------
# Theme + UI resolution
# ---------------------------------------------------------------------------


def _get_active_theme() -> type[Theme] | None:
    """Find the one explicitly enabled theme. Falls back to --default-theme."""
    from app.api.pipes import _load_themes

    themes = _load_themes()
    try:
        from app.db import get_all_plugin_states

        states = {s["name"]: s for s in get_all_plugin_states("theme")}
        for t in themes:
            state = states.get(t.name)
            if state and state["enabled"]:
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
    from app.api.pipes import _load_uis

    uis = _load_uis()
    ui_name = app.state.ui_name
    ui = next((u for u in uis if u.name == ui_name), None)
    if ui:
        html_file = ui.static_dir / ui.html
        if html_file.exists():
            content = html_file.read_text()
            theme = _get_active_theme()
            if theme:
                css_link = f'<link rel="stylesheet" href="/themes/{theme.name}/{theme.css}" data-shenas-theme>'
                content = content.replace("</head>", f"  {css_link}\n  </head>")
            return HTMLResponse(content=content)
    return HTMLResponse(content=_FALLBACK_HTML.format(ui_name=ui_name))


_FALLBACK_HTML = """\
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>shenas</title>
  <style>body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #222; }}</style>
  </head>
  <body>
    <h1>shenas</h1>
    <p>UI plugin <code>{ui_name}</code> is not installed.</p>
    <p>Install it with: <code>shenasctl ui add {ui_name}</code></p>
    <p>Or start with a different UI: <code>shenas --ui other-name</code></p>
    <h2>API</h2>
    <ul>
      <li><a href="/api/health">GET /api/health</a></li>
      <li><a href="/api/tables">GET /api/tables</a></li>
      <li><a href="/api/db/status">GET /api/db/status</a></li>
      <li>GET /api/plugins/{{kind}}</li>
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
# HTML routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the active UI plugin as the app shell."""
    return _serve_ui_html()


@app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(path: str) -> HTMLResponse:  # noqa: ARG001
    """SPA fallback -- serve UI HTML for any unmatched route."""
    return _serve_ui_html()
