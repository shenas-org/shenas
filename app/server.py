"""Shenas metrics server -- FastAPI app with plugin discovery."""

from __future__ import annotations

import asyncio as _asyncio
import os as _os
import pathlib as _pathlib
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
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
# API endpoints (non-router, app-level)
# ---------------------------------------------------------------------------


@app.get("/api/theme")
def active_theme() -> dict[str, str | None]:
    """Return the active theme name and CSS URL."""
    theme = _get_active_theme()
    if theme:
        return {"name": theme.name, "css": f"/themes/{theme.name}/{theme.css}"}
    return {"name": app.state.default_theme, "css": None}


@app.get("/api/dependencies")
def plugin_dependencies() -> dict[str, list[str]]:
    """Return cross-plugin dependencies from Python package metadata."""
    from importlib.metadata import distributions

    prefixes = {
        "shenas-pipe-": "pipe",
        "shenas-schema-": "schema",
        "shenas-component-": "component",
        "shenas-ui-": "ui",
        "shenas-theme-": "theme",
    }
    result: dict[str, list[str]] = {}
    for dist in distributions():
        pkg_name = dist.metadata["Name"]
        if pkg_name.endswith("-core"):
            continue
        kind = None
        for prefix, k in prefixes.items():
            if pkg_name.startswith(prefix):
                kind = k
                plugin_name = pkg_name.removeprefix(prefix)
                break
        if not kind:
            continue
        deps = []
        for req in dist.requires or []:
            req_name = req.split(";")[0].split("[")[0].split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip()
            for dep_prefix, dep_kind in prefixes.items():
                if req_name.startswith(dep_prefix) and not req_name.endswith("-core"):
                    deps.append(f"{dep_kind}:{req_name.removeprefix(dep_prefix)}")
        if deps:
            result[f"{kind}:{plugin_name}"] = deps
    return result


@app.get("/api/logs")
def get_logs(
    limit: int = 100,
    severity: str | None = None,
    search: str | None = None,
    pipe: str | None = None,
) -> list[dict[str, Any]]:
    """Query telemetry logs."""
    from app.db import connect

    limit = max(1, min(limit, 1000))
    con = connect(read_only=True)
    cur = con.cursor()
    try:
        cur.execute("USE db")
        conditions = []
        params: list[Any] = []
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if search:
            conditions.append("body LIKE ?")
            params.append(f"%{search}%")
        if pipe:
            conditions.append("(body LIKE ? OR attributes LIKE ?)")
            params.extend([f"%{pipe}%", f"%{pipe}%"])
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = cur.execute(
            f"SELECT timestamp, trace_id, span_id, severity, body, attributes, service_name "
            f"FROM telemetry.logs{where} ORDER BY timestamp DESC LIMIT {limit}",
            params,
        ).fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=False)) for r in rows]
    except Exception:
        return []
    finally:
        cur.close()


@app.get("/api/spans")
def get_spans(
    limit: int = 100,
    search: str | None = None,
    pipe: str | None = None,
) -> list[dict[str, Any]]:
    """Query telemetry spans."""
    from app.db import connect

    limit = max(1, min(limit, 1000))
    con = connect(read_only=True)
    cur = con.cursor()
    try:
        cur.execute("USE db")
        conditions = []
        params: list[Any] = []
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        if pipe:
            conditions.append("(name LIKE ? OR attributes LIKE ?)")
            params.extend([f"%{pipe}%", f"%{pipe}%"])
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = cur.execute(
            f"SELECT trace_id, span_id, parent_span_id, name, kind, service_name, "
            f"status_code, start_time, end_time, duration_ms, attributes "
            f"FROM telemetry.spans{where} ORDER BY start_time DESC LIMIT {limit}",
            params,
        ).fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=False)) for r in rows]
    except Exception:
        return []
    finally:
        cur.close()


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


@app.get("/api/hotkeys")
def get_hotkeys_endpoint() -> dict[str, str]:
    from app.db import get_hotkeys

    return get_hotkeys()


@app.put("/api/hotkeys/{action_id}")
def set_hotkey(action_id: str, body: dict[str, str]) -> dict[str, bool]:
    from app.db import set_hotkey

    binding = body.get("binding", "")
    set_hotkey(action_id, binding)
    return {"ok": True}


@app.delete("/api/hotkeys/{action_id}")
def delete_hotkey(action_id: str) -> dict[str, bool]:
    from app.db import set_hotkey

    set_hotkey(action_id, "")
    return {"ok": True}


@app.post("/api/hotkeys/reset")
def reset_hotkeys() -> dict[str, bool]:
    from app.db import reset_hotkeys

    reset_hotkeys()
    return {"ok": True}


@app.get("/api/workspace")
def get_workspace_endpoint() -> dict[str, Any]:
    from app.db import get_workspace

    return get_workspace()


@app.put("/api/workspace")
async def save_workspace_state(_request: Request) -> dict[str, bool]:
    from app.db import save_workspace

    body = await _request.json()
    save_workspace(body)
    return {"ok": True}


@app.get("/api/components")
def list_component_metadata() -> list[dict[str, str]]:
    """Return component metadata needed by the UI shell."""
    from app.api.pipes import _load_components
    from app.db import is_plugin_enabled

    return [
        {
            "name": c.name,
            "display_name": c.display_name,
            "tag": c.tag,
            "js": f"/components/{c.name}/{c.entrypoint}",
            "description": c.description,
        }
        for c in _load_components(include_internal=False)
        if is_plugin_enabled("component", c.name)
    ]


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the active UI plugin as the app shell."""
    return _serve_ui_html()


@app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(path: str) -> HTMLResponse:  # noqa: ARG001
    """SPA fallback -- serve UI HTML for any unmatched route."""
    return _serve_ui_html()
