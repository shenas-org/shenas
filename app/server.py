# TODO: API authentication should be added when the UI is exposed beyond localhost.
# Currently relies on HTTPS + localhost binding for security. See discussion in
# commit history about bearer tokens, mTLS, and Unix sockets as future options.

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import entry_points
from pathlib import Path as _Path
from typing import Any  # noqa: F401

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.db import DB_PATH


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from telemetry.setup import init_telemetry

    init_telemetry("shenas-server")
    FastAPIInstrumentor.instrument_app(application)
    yield


app = FastAPI(title="shenas ui", docs_url=None, redoc_url=None, lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=str(_Path(__file__).parent / "static")), name="static")
app.include_router(api_router)


def _discover_plugins(group: str) -> list[dict[str, Any]]:
    """Discover installed plugins via entry points."""
    plugins: list[dict[str, Any]] = []
    for ep in entry_points(group=group):
        try:
            plugin = ep.load()
            if isinstance(plugin, dict) and "static_dir" in plugin:
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


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    components = _discover_plugins("shenas.components")
    ui_plugins = _discover_plugins("shenas.ui")

    def _plugin_cards(plugins: list[dict[str, Any]], url_prefix: str, install_cmd: str) -> str:
        if plugins:
            return "\n".join(
                f'      <li><a href="/{url_prefix}/{p["name"]}/{p.get("html", "index.html")}">'
                f'{p["name"]}</a> <span style="color:#888">v{p.get("version", "?")}</span>'
                f" -- {p.get('description', '')}</li>"
                for p in plugins
            )
        return f"      <li>None installed. Install with: shenasctl {install_cmd} add &lt;name&gt;</li>"

    component_cards = _plugin_cards(components, "components", "component")
    ui_cards = _plugin_cards(ui_plugins, "ui", "ui")
    html = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>shenas ui</title>
    <style>
      body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #222; }}
      a {{ color: #0066cc; }}
      li {{ margin: 0.4rem 0; }}
      .header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
      .header img {{ width: 48px; height: 48px; }}
      .header h1 {{ margin: 0; }}
    </style>
  </head>
  <body>
    <div class="header">
      <img src="/static/images/shenas.png" alt="shenas">
      <h1>shenas ui</h1>
    </div>
    <p>Database: <code>{DB_PATH}</code></p>
    <h2>UI</h2>
    <ul>
{ui_cards}
    </ul>
    <h2>Components</h2>
    <ul>
{component_cards}
    </ul>
    <h2>API</h2>
    <ul>
      <li><a href="/api/tables">GET /api/tables</a> — list metric tables</li>
      <li>GET /api/query?sql=... — returns Arrow IPC stream</li>
      <li><a href="/api/config">GET /api/config</a> — list config entries</li>
      <li><a href="/api/db/status">GET /api/db/status</a> — database status</li>
      <li>GET /api/plugins/{{kind}} — list installed plugins</li>
      <li>POST /api/sync — sync all pipes (SSE)</li>
    </ul>
  </body>
</html>"""
    return HTMLResponse(content=html)
