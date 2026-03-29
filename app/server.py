# TODO: API authentication should be added when the UI is exposed beyond localhost.
# Currently relies on HTTPS + localhost binding for security. See discussion in
# commit history about bearer tokens, mTLS, and Unix sockets as future options.

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import entry_points
from pathlib import Path as _Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from telemetry.setup import init_telemetry

    init_telemetry("shenas-server")
    FastAPIInstrumentor.instrument_app(application)
    yield


app = FastAPI(title="shenas", docs_url=None, redoc_url=None, lifespan=_lifespan)
app.state.ui_name = "default"  # overridden by server_cli.py
app.mount("/static", StaticFiles(directory=str(_Path(__file__).parent / "static")), name="static")
_vendor_dir = _Path(__file__).parent.parent / "vendor" / "dist"
if _vendor_dir.is_dir():
    app.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")
app.include_router(api_router)


def _discover_plugins(group: str) -> list[dict[str, Any]]:
    """Discover installed plugins via entry points."""
    plugins: list[dict[str, Any]] = []
    for ep in entry_points(group=group):
        try:
            plugin = ep.load()
            if isinstance(plugin, dict) and "static_dir" in plugin and not plugin.get("internal"):
                plugins.append(plugin)
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
            return HTMLResponse(content=html_file.read_text())
    return HTMLResponse(content=_FALLBACK_HTML.format(ui_name=app.state.ui_name))


@app.get("/api/components")
def list_component_metadata() -> list[dict[str, str]]:
    """Return component metadata needed by the UI shell (tag, entrypoint, JS URL)."""
    components = _discover_plugins("shenas.components")
    return [
        {
            "name": c["name"],
            "tag": c.get("tag", f"shenas-{c['name']}"),
            "js": f"/components/{c['name']}/{c.get('entrypoint', c['name'] + '.js')}",
            "description": c.get("description", ""),
        }
        for c in components
    ]


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the active UI plugin as the app shell."""
    return _serve_ui_html()


@app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(request: Request, path: str) -> HTMLResponse:
    """SPA catch-all: serve the UI HTML for any path not matched by API or static mounts."""
    return _serve_ui_html()
