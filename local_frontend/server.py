# TODO: API authentication should be added when the UI is exposed beyond localhost.
# Currently relies on HTTPS + localhost binding for security. See discussion in
# commit history about bearer tokens, mTLS, and Unix sockets as future options.

from importlib.metadata import entry_points
from pathlib import Path as _Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from cli.db import DB_PATH
from local_frontend.api import api_router

app = FastAPI(title="shenas ui", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(_Path(__file__).parent / "static")), name="static")
app.include_router(api_router)


def _discover_components() -> list[dict]:
    """Discover installed components via entry points."""
    components = []
    for ep in entry_points(group="shenas.components"):
        try:
            comp = ep.load()
            if isinstance(comp, dict) and "static_dir" in comp:
                components.append(comp)
        except Exception:
            pass
    return components


def _mount_components() -> None:
    """Mount static dirs for each installed component."""
    for comp in _discover_components():
        static_dir = comp["static_dir"]
        if static_dir.is_dir():
            app.mount(
                f"/components/{comp['name']}",
                StaticFiles(directory=str(static_dir)),
                name=f"component-{comp['name']}",
            )


_mount_components()


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    components = _discover_components()
    if components:
        cards = "\n".join(
            f'      <li><a href="/components/{c["name"]}/{c.get("html", "index.html")}">'
            f'{c["name"]}</a> <span style="color:#888">v{c.get("version", "?")}</span>'
            f" — {c.get('description', '')}</li>"
            for c in components
        )
    else:
        cards = "      <li>No components installed. Install with: shenas component add &lt;name&gt;</li>"
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
    <h2>Components</h2>
    <ul>
{cards}
    </ul>
    <h2>API</h2>
    <ul>
      <li><a href="/api/tables">GET /api/tables</a> — list metric tables</li>
      <li>GET /api/query?sql=... — returns Arrow IPC stream</li>
      <li><a href="/api/config">GET /api/config</a> — list config entries</li>
      <li><a href="/api/db/status">GET /api/db/status</a> — database status</li>
      <li>GET /api/packages/{{kind}} — list installed packages</li>
      <li>POST /api/sync — sync all pipes (SSE)</li>
    </ul>
  </body>
</html>"""
    return HTMLResponse(content=html)
