from importlib.metadata import entry_points

import duckdb
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from cli.db import DB_PATH, connect

app = FastAPI(title="shenas ui", docs_url=None, redoc_url=None)


async def _auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Check bearer token for /api/* routes."""
    if request.url.path.startswith("/api/"):
        token = getattr(request.app.state, "api_token", None)
        if token is not None:
            auth = request.headers.get("authorization", "")
            if auth != f"Bearer {token}":
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


app.middleware("http")(_auth_middleware)


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


def _get_token(request: Request) -> str:
    return getattr(request.app.state, "api_token", "")


def _inject_token(html: str, token: str) -> str:
    """Inject the API token as a meta tag into an HTML page."""
    return html.replace("<head>", f'<head>\n    <meta name="shenas-api-token" content="{token}">', 1)


def _mount_components() -> None:
    """Mount static dirs and register HTML routes for each installed component."""
    for comp in _discover_components():
        static_dir = comp["static_dir"]
        if not static_dir.is_dir():
            continue

        comp_name = comp["name"]

        # Register a dynamic route for the component's HTML file
        # This injects the API token before serving
        html_file = comp.get("html", "index.html")
        html_path = static_dir / html_file

        if html_path.exists():
            # Capture variables for closure
            _html_content = html_path.read_text()
            _route_path = f"/components/{comp_name}/{html_file}"

            def _make_handler(content: str):  # type: ignore[no-untyped-def]
                def handler(request: Request) -> HTMLResponse:
                    return HTMLResponse(content=_inject_token(content, _get_token(request)))

                return handler

            app.get(_route_path, response_class=HTMLResponse)(_make_handler(_html_content))

        # Mount static files for JS/CSS/etc (routes take precedence for HTML)
        app.mount(
            f"/components/{comp_name}",
            StaticFiles(directory=str(static_dir)),
            name=f"component-{comp_name}",
        )


_mount_components()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    token = _get_token(request)
    components = _discover_components()
    if components:
        cards = "\n".join(
            f'      <li><a href="/components/{c["name"]}/{c.get("html", "index.html")}">'
            f'{c["name"]}</a> <span style="color:#888">v{c.get("version", "?")}</span>'
            f" — {c.get('description', '')}</li>"
            for c in components
        )
    else:
        cards = "      <li>No components installed. Install with: shenas install component &lt;name&gt;</li>"
    html = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="shenas-api-token" content="{token}">
    <title>shenas ui</title>
    <style>
      body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #222; }}
      a {{ color: #0066cc; }}
      li {{ margin: 0.4rem 0; }}
    </style>
  </head>
  <body>
    <h1>shenas ui</h1>
    <p>Database: <code>{DB_PATH}</code></p>
    <h2>Components</h2>
    <ul>
{cards}
    </ul>
    <h2>API</h2>
    <ul>
      <li>GET /api/tables — list canonical metric tables (requires Authorization header)</li>
      <li>GET /api/query?sql=... — Arrow IPC stream (requires Authorization header)</li>
    </ul>
  </body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/tables")
def api_tables() -> list[dict]:
    con = connect(read_only=True)
    rows = con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema IN ('garmin', 'metrics') ORDER BY table_schema, table_name"
    ).fetchall()
    con.close()
    return [{"schema": r[0], "table": r[1]} for r in rows]


@app.get("/api/query")
def api_query(sql: str) -> Response:
    import pyarrow as pa

    con = connect(read_only=True)
    try:
        arrow_table = con.execute(sql).arrow().read_all()
    except duckdb.Error as exc:
        con.close()
        return Response(content=str(exc), status_code=400, media_type="text/plain")
    con.close()

    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, arrow_table.schema) as writer:
        writer.write_table(arrow_table)

    return Response(content=sink.getvalue().to_pybytes(), media_type="application/vnd.apache.arrow.stream")
