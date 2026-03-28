"""Query and table listing endpoints (moved from server.py)."""

import duckdb
from fastapi import APIRouter, Response

from app.db import connect

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/tables")
def api_tables() -> list[dict]:
    con = connect(read_only=True)
    rows = con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema', 'main') "
        "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
        "ORDER BY table_schema, table_name"
    ).fetchall()
    con.close()
    return [{"schema": r[0], "table": r[1]} for r in rows]


@router.get("/query")
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
