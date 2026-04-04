"""Query and table listing endpoints."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Response

from app.db import cursor
from app.models import HealthResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/tables")
def api_tables() -> list[dict[str, str]]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'main') "
            "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
            "ORDER BY table_schema, table_name"
        ).fetchall()
    return [{"schema": r[0], "table": r[1]} for r in rows]


@router.get("/query")
def api_query(sql: str) -> Response:
    import pyarrow as pa

    try:
        with cursor() as cur:
            arrow_table = cur.execute(sql).arrow().read_all()
    except duckdb.Error as exc:
        return Response(content=str(exc), status_code=400, media_type="text/plain")

    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, arrow_table.schema) as writer:
        writer.write_table(arrow_table)

    return Response(content=sink.getvalue().to_pybytes(), media_type="application/vnd.apache.arrow.stream")
