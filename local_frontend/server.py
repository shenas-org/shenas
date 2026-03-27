# TODO: API authentication should be added when the UI is exposed beyond localhost.
# Currently relies on HTTPS + localhost binding for security. See discussion in
# commit history about bearer tokens, mTLS, and Unix sockets as future options.

from importlib.metadata import entry_points

import duckdb
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from cli.db import DB_PATH, connect

app = FastAPI(title="shenas ui", docs_url=None, redoc_url=None)


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
      <li><a href="/api/tables">GET /api/tables</a> — list canonical metric tables</li>
      <li>GET /api/query?sql=... — returns Arrow IPC stream</li>
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
