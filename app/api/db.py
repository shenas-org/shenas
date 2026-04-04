"""Database status API endpoint."""

from __future__ import annotations

import os
import re
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException

from app.db import DB_PATH, cursor
from app.models import DBStatusResponse, OkResponse, SchemaInfo, TableStats

router = APIRouter(prefix="/db", tags=["db"])


def _discover_schemas() -> dict[str, list[str]]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'main') "
            "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
            "ORDER BY table_schema, table_name"
        ).fetchall()
    schemas: dict[str, list[str]] = {}
    for schema, table in rows:
        schemas.setdefault(schema, []).append(table)
    return schemas


def _table_stats(schema: str, name: str) -> TableStats:
    qualified = f'"{schema}"."{name}"'
    with cursor() as cur:
        row = cur.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
        rows = row[0] if row else 0
        cols = len(cur.execute(f"DESCRIBE {qualified}").fetchall())
        earliest = None
        latest = None
        for date_col in ("date", "calendar_date", "start_time_local"):
            try:
                res = cur.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
                if res is None:
                    continue
                earliest = str(res[0])[:10] if res[0] else None
                latest = str(res[1])[:10] if res[1] else None
                break
            except duckdb.Error:
                continue
    return TableStats(name=name, rows=rows, earliest=earliest, latest=latest, cols=cols)


@router.get("/status")
def db_status() -> DBStatusResponse:
    if os.environ.get("SHENAS_DB_KEY"):
        key_source = "env"
    else:
        try:
            import keyring

            key = keyring.get_password("shenas", "db_key")
            key_source = "keyring" if key else "not_set"
        except Exception:
            key_source = "unavailable"

    db_path = str(DB_PATH)
    size_mb = None
    schemas_data: list[SchemaInfo] = []

    if DB_PATH.exists():
        size_mb = round(DB_PATH.stat().st_size / (1024 * 1024), 1)
        try:
            schemas = _discover_schemas()
            for schema_name, tables in schemas.items():
                table_list = [_table_stats(schema_name, name) for name in tables if not name.startswith("_dlt_")]
                schemas_data.append(SchemaInfo(name=schema_name, tables=table_list))
        except Exception:
            pass

    return DBStatusResponse(
        key_source=key_source,
        db_path=db_path,
        size_mb=size_mb,
        schemas=schemas_data,
    )


_INTERNAL_SCHEMAS = {"config", "auth", "shenas_system", "telemetry"}


@router.get("/tables")
def db_tables() -> dict[str, list[str]]:
    """Return schema -> table names mapping (excludes internal and dlt tables)."""
    try:
        schemas = _discover_schemas()
        return {
            s: [t for t in tables if not t.startswith("_dlt_")] for s, tables in schemas.items() if s not in _INTERNAL_SCHEMAS
        }
    except Exception:
        return {}


def _load_schema_plugins() -> dict[str, list[str]]:
    """Load schema plugin name -> table names from entry points."""
    from app.api.pipes import _load_schemas

    return {s.name: sorted(s.tables) for s in _load_schemas()}


@router.get("/schema-tables")
def schema_plugin_tables() -> dict[str, list[str]]:
    """Return DuckDB schema -> tables for installed schema plugins."""
    plugins = _load_schema_plugins()
    all_tables: list[str] = []
    for tables in plugins.values():
        all_tables.extend(tables)
    return {"metrics": sorted(set(all_tables))} if all_tables else {}


@router.get("/schema-plugins")
def schema_plugin_ownership() -> dict[str, list[str]]:
    """Return schema plugin name -> list of table names it owns."""
    return _load_schema_plugins()


_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@router.get("/preview/{schema}/{table}")
def table_preview(schema: str, table: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return the first N rows of a table, ordered by primary key descending."""
    if not _IDENTIFIER_RE.match(schema) or not _IDENTIFIER_RE.match(table):
        raise HTTPException(status_code=400, detail="Invalid schema or table name")
    limit = min(max(1, limit), 500)
    qualified = f'"{schema}"."{table}"'
    with cursor() as cur:
        # Try to find PK columns for ordering
        pk_cols = [
            r[0]
            for r in cur.execute(
                "SELECT column_name FROM information_schema.key_column_usage "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
        ]
        order_clause = " ORDER BY " + ", ".join(f'"{c}" DESC' for c in pk_cols) if pk_cols else ""
        rows = cur.execute(f"SELECT * FROM {qualified}{order_clause} LIMIT {limit}").fetchall()
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in rows]


@router.post("/keygen")
def db_keygen() -> OkResponse:
    """Generate a database encryption key and store it in the OS keyring."""
    from app.db import generate_db_key, set_db_key

    key = generate_db_key()
    set_db_key(key)
    return OkResponse(ok=True)
