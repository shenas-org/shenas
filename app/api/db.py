"""Database status API endpoint."""

from __future__ import annotations

import os

import duckdb
from fastapi import APIRouter

from app.db import DB_PATH, connect
from app.models import DBStatusResponse, OkResponse, SchemaInfo, TableStats

router = APIRouter(prefix="/db", tags=["db"])


def _discover_schemas(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    rows = con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema', 'main') "
        "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
        "ORDER BY table_schema, table_name"
    ).fetchall()
    schemas: dict[str, list[str]] = {}
    for schema, table in rows:
        schemas.setdefault(schema, []).append(table)
    return schemas


def _table_stats(con: duckdb.DuckDBPyConnection, schema: str, name: str) -> TableStats:
    qualified = f"{schema}.{name}"
    row = con.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
    rows = row[0] if row else 0
    cols = len(con.execute(f"DESCRIBE {qualified}").fetchall())
    earliest = None
    latest = None
    for date_col in ("date", "calendar_date", "start_time_local"):
        try:
            res = con.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
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
    # Key source
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
            con = connect(read_only=True)
            schemas = _discover_schemas(con)
            for schema_name, tables in schemas.items():
                table_list = []
                for name in tables:
                    if not name.startswith("_dlt_"):
                        table_list.append(_table_stats(con, schema_name, name))
                schemas_data.append(SchemaInfo(name=schema_name, tables=table_list))
        except Exception:
            pass

    return DBStatusResponse(
        key_source=key_source,
        db_path=db_path,
        size_mb=size_mb,
        schemas=schemas_data,
    )


@router.get("/tables")
def db_tables() -> dict[str, list[str]]:
    """Return schema -> table names mapping (excludes dlt internal tables)."""
    try:
        con = connect(read_only=True)
        schemas = _discover_schemas(con)
        return {s: [t for t in tables if not t.startswith("_dlt_")] for s, tables in schemas.items()}
    except Exception:
        return {}


@router.get("/schema-tables")
def schema_plugin_tables() -> dict[str, list[str]]:
    """Return DuckDB schema -> tables for installed schema plugins.

    Schema plugins define canonical tables (e.g. metrics.daily_hrv).
    This endpoint introspects them to find the actual DuckDB schemas and tables.
    """
    from importlib.metadata import entry_points

    result: dict[str, list[str]] = {}
    for ep in entry_points(group="shenas.schemas"):
        if ep.name == "core":
            continue
        try:
            schema_dict = ep.load()
            tables = schema_dict.get("tables", []) if isinstance(schema_dict, dict) else []
            if tables:
                result.setdefault("metrics", []).extend(tables)
        except Exception:
            continue
    for schema in result:
        result[schema] = sorted(set(result[schema]))
    return result


@router.post("/keygen")
def db_keygen() -> OkResponse:
    """Generate a database encryption key and store it in the OS keyring."""
    from app.db import generate_db_key, set_db_key

    key = generate_db_key()
    set_db_key(key)
    return OkResponse(ok=True)
