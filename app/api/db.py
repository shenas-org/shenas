"""Database status API endpoint."""

from __future__ import annotations

import re
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException

from app.database import cursor
from app.models import OkResponse

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


_INTERNAL_SCHEMAS = {
    "config",
    "auth",
    "shenas",
    "plugins",
    "transforms",
    "catalog",
    "analysis",
    "cache",
    "mesh",
    "ui",
    "telemetry",
}


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
    from shenas_datasets.core.dataset import Dataset

    return {s.name: sorted(s.tables) for s in Dataset.load_all(include_internal=False)}


@router.get("/schema-tables")
def schema_plugin_tables() -> dict[str, list[str]]:
    """Return DuckDB schema -> tables for installed schema plugins."""
    plugins = _load_schema_plugins()
    all_tables: list[str] = []
    for tables in plugins.values():
        all_tables.extend(tables)
    return {"datasets": sorted(set(all_tables))} if all_tables else {}


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
        # Order by PK if available, else by first column
        pk_cols = [
            r[0]
            for r in cur.execute(
                "SELECT column_name FROM information_schema.key_column_usage "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
        ]
        if not pk_cols:
            # dlt doesn't create SQL PKs -- fall back to first column
            first = cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position LIMIT 1",
                [schema, table],
            ).fetchone()
            if first:
                pk_cols = [first[0]]
        order_clause = " ORDER BY " + ", ".join(f'"{c}" DESC' for c in pk_cols) if pk_cols else ""
        rows = cur.execute(f"SELECT * FROM {qualified}{order_clause} LIMIT {limit}").fetchall()
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in rows]


@router.delete("/schema/{schema_plugin}/flush")
def flush_schema(schema_plugin: str) -> dict[str, Any]:
    """Delete all rows from tables owned by a schema plugin."""
    plugins = _load_schema_plugins()
    tables = plugins.get(schema_plugin)
    if not tables:
        raise HTTPException(status_code=404, detail=f"Schema plugin not found: {schema_plugin}")
    total = 0
    with cursor() as cur:
        for table in tables:
            if not _IDENTIFIER_RE.match(table):
                continue
            try:
                row = cur.execute(f'SELECT count(*) FROM "datasets"."{table}"').fetchone()
                cur.execute(f'DELETE FROM "datasets"."{table}"')
                total += row[0] if row else 0
            except duckdb.CatalogException:
                continue
    return {"schema": schema_plugin, "tables": tables, "rows_deleted": total}


@router.post("/keygen")
def db_keygen() -> OkResponse:
    """Generate a database encryption key and store it in the OS keyring."""
    from app.database import generate_db_key, set_db_key

    key = generate_db_key()
    set_db_key(key)
    return OkResponse(ok=True)
