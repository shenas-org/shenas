# TODO: API authentication should be added when the UI is exposed beyond localhost.
# Currently relies on HTTPS + localhost binding for security. See discussion in
# commit history about bearer tokens, mTLS, and Unix sockets as future options.

from __future__ import annotations

from contextlib import asynccontextmanager
from importlib.metadata import entry_points
from pathlib import Path as _Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    import asyncio

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    from app.telemetry.dispatcher import set_loop
    from app.telemetry.setup import init_telemetry

    init_telemetry("shenas-server")
    set_loop(asyncio.get_running_loop())
    FastAPIInstrumentor.instrument_app(application)
    yield


app = FastAPI(title="shenas", docs_url=None, redoc_url=None, lifespan=_lifespan)
import os as _os  # noqa: E402

app.state.ui_name = _os.environ.get("SHENAS_UI", "default")
app.state.default_theme = _os.environ.get("SHENAS_DEFAULT_THEME", "default")
app.mount("/static", StaticFiles(directory=str(_Path(__file__).parent / "static")), name="static")
_vendor_dir = _Path(__file__).parent / "vendor" / "dist"
if _vendor_dir.is_dir():
    app.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")
app.include_router(api_router)


def _discover_plugins(group: str, include_internal: bool = True) -> list[dict[str, Any]]:
    """Discover installed plugins via entry points.

    Supports both ABC classes (StaticPlugin subclasses) and legacy dicts.
    """
    from shenas_pipes.core.abc import StaticPlugin

    plugins: list[dict[str, Any]] = []
    for ep in entry_points(group=group):
        try:
            obj = ep.load()
            if isinstance(obj, type) and issubclass(obj, StaticPlugin):
                plugin = {
                    "name": obj.name,
                    "display_name": obj.display_name,
                    "description": obj.description,
                    "static_dir": obj.static_dir,
                    "internal": obj.internal,
                }
                # Copy kind-specific attributes
                for attr in ("css", "html", "entrypoint", "tag"):
                    if hasattr(obj, attr):
                        plugin[attr] = getattr(obj, attr)
                if include_internal or not plugin.get("internal"):
                    plugins.append(plugin)
            elif isinstance(obj, dict) and "static_dir" in obj and (include_internal or not obj.get("internal")):
                plugins.append(obj)
        except Exception:
            pass
    return plugins


def _mount_static_plugins(group: str, url_prefix: str) -> None:
    """Mount static dirs for plugins discovered via the given entry point group."""
    for plugin in _discover_plugins(group):
        static_dir = plugin["static_dir"]
        if static_dir.is_dir():
            app.mount(
                f"/{url_prefix}/{plugin['name']}",
                StaticFiles(directory=str(static_dir)),
                name=f"{url_prefix}-{plugin['name']}",
            )


_mount_static_plugins("shenas.components", "components")
_mount_static_plugins("shenas.ui", "ui")
_mount_static_plugins("shenas.themes", "themes")


def _get_active_theme() -> dict[str, Any] | None:
    """Find the one explicitly enabled theme. Falls back to --default-theme."""
    themes = _discover_plugins("shenas.themes")
    try:
        from app.db import get_all_plugin_states

        states = {s["name"]: s for s in get_all_plugin_states("theme")}
        for plugin in themes:
            state = states.get(plugin["name"])
            if state and state["enabled"]:
                return plugin
    except Exception:
        pass
    # Fallback: no theme explicitly enabled -- use --default-theme
    fallback = getattr(app.state, "default_theme", "default")
    for plugin in themes:
        if plugin["name"] == fallback:
            return plugin
    return themes[0] if themes else None


def _get_active_ui() -> dict[str, Any] | None:
    """Find the active UI plugin."""
    ui_name = app.state.ui_name
    for plugin in _discover_plugins("shenas.ui"):
        if plugin["name"] == ui_name:
            return plugin
    return None


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


def _serve_ui_html() -> HTMLResponse:
    """Read and serve the active UI plugin's HTML from disk, or a fallback."""
    ui = _get_active_ui()
    if ui:
        static_dir = ui["static_dir"]
        html_file = static_dir / ui.get("html", "index.html")
        if html_file.exists():
            content = html_file.read_text()
            theme = _get_active_theme()
            if theme and theme.get("css"):
                css_link = f'<link rel="stylesheet" href="/themes/{theme["name"]}/{theme["css"]}" data-shenas-theme>'
                content = content.replace("</head>", f"  {css_link}\n  </head>")
            return HTMLResponse(content=content)
    return HTMLResponse(content=_FALLBACK_HTML.format(ui_name=app.state.ui_name))


@app.get("/api/theme")
def active_theme() -> dict[str, str | None]:
    """Return the active theme name and CSS URL."""
    theme = _get_active_theme()
    if theme and theme.get("css"):
        return {"name": theme["name"], "css": f"/themes/{theme['name']}/{theme['css']}"}
    return {"name": app.state.default_theme, "css": None}


@app.get("/api/dependencies")
def plugin_dependencies() -> dict[str, list[str]]:
    """Return cross-plugin dependencies from Python package metadata.

    Reads importlib.metadata.requires() for all shenas-* packages.
    Returns {"{kind}:{name}": ["{dep_kind}:{dep_name}", ...]}
    """
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
    limit: int = 100, severity: str | None = None, search: str | None = None, pipe: str | None = None
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
def get_spans(limit: int = 100, search: str | None = None, pipe: str | None = None) -> list[dict[str, Any]]:
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
    """SSE stream of new log entries as they arrive."""
    import asyncio
    import json

    from app.telemetry.dispatcher import subscribe, unsubscribe

    async def _generate() -> AsyncIterator[str]:
        q = subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                    if event["type"] == "logs":
                        for row in event["data"]:
                            yield f"data: {json.dumps(row, default=str)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(q)

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.get("/api/stream/spans")
async def stream_spans() -> StreamingResponse:
    """SSE stream of new span entries as they arrive."""
    import asyncio
    import json

    from app.telemetry.dispatcher import subscribe, unsubscribe

    async def _generate() -> AsyncIterator[str]:
        q = subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                    if event["type"] == "spans":
                        for row in event["data"]:
                            yield f"data: {json.dumps(row, default=str)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(q)

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.get("/api/hotkeys")
def get_hotkeys_api() -> dict[str, str]:
    """Get all hotkey bindings."""
    from app.db import get_hotkeys

    return get_hotkeys()


@app.put("/api/hotkeys/{action_id}")
def set_hotkey_api(action_id: str, body: dict[str, str]) -> dict[str, bool]:
    """Set a hotkey binding for an action."""
    from app.db import set_hotkey

    binding = body.get("binding", "")
    if binding:
        set_hotkey(action_id, binding)
    else:
        from app.db import delete_hotkey

        delete_hotkey(action_id)
    return {"ok": True}


@app.delete("/api/hotkeys/{action_id}")
def delete_hotkey_api(action_id: str) -> dict[str, bool]:
    """Remove a hotkey binding."""
    from app.db import delete_hotkey

    delete_hotkey(action_id)
    return {"ok": True}


@app.post("/api/hotkeys/reset")
def reset_hotkeys_api() -> dict[str, bool]:
    """Reset all hotkeys to defaults."""
    from app.db import reset_hotkeys

    reset_hotkeys()
    return {"ok": True}


@app.get("/api/workspace")
def get_workspace_state() -> dict[str, Any]:
    """Get the persisted workspace state (open tabs, active tab)."""
    try:
        from app.db import get_workspace

        return get_workspace()
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Failed to load workspace")
        return {}


@app.put("/api/workspace")
def save_workspace_state(body: dict[str, Any]) -> dict[str, bool]:
    """Save the workspace state."""
    try:
        from app.db import save_workspace

        save_workspace(body)
        return {"ok": True}
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Failed to save workspace")
        return {"ok": False}


@app.get("/api/components")
def list_component_metadata() -> list[dict[str, str]]:
    """Return component metadata needed by the UI shell (tag, entrypoint, JS URL)."""
    from app.db import is_plugin_enabled

    components = _discover_plugins("shenas.components", include_internal=False)
    return [
        {
            "name": c["name"],
            "display_name": c.get("display_name", c["name"]),
            "tag": c.get("tag", f"shenas-{c['name']}"),
            "js": f"/components/{c['name']}/{c.get('entrypoint', c['name'] + '.js')}",
            "description": c.get("description", ""),
        }
        for c in components
        if is_plugin_enabled("component", c["name"])
    ]


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the active UI plugin as the app shell."""
    return _serve_ui_html()


@app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(_request: Request, path: str) -> HTMLResponse:
    """SPA catch-all: serve the UI HTML for paths without file extensions."""
    if "." in path.rsplit("/", maxsplit=1)[-1]:
        return HTMLResponse(status_code=404, content="Not found")
    return _serve_ui_html()
