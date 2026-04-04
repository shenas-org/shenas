"""Auth credential storage in the encrypted DuckDB using typed dataclass tables.

Each pipe defines an auth dataclass (same pattern as config tables). The system
creates a table per auth class in the `auth` schema, with full type information
and metadata available for frontend UI generation via introspection.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import duckdb

from shenas_schemas.core.ddl import generate_ddl
from shenas_schemas.core.introspect import table_metadata


_ensured_tables: set[str] = set()


def ensure_auth_table(con: duckdb.DuckDBPyConnection, auth_cls: type) -> None:
    """Create the auth schema and table if they don't exist, and add missing columns."""
    table = auth_cls.__table__
    if table in _ensured_tables:
        return

    cur = con.cursor()
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS auth")
        ddl = generate_ddl(auth_cls).replace("metrics.", "auth.")
        cur.execute(ddl)

        # Add any columns that exist in the dataclass but not yet in the table
        existing = {
            r[0]
            for r in cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'auth' AND table_name = ?",
                [table],
            ).fetchall()
        }
        meta = table_metadata(auth_cls)
        for col in meta["columns"]:
            if col["name"] not in existing:
                db_type = col.get("db_type", "VARCHAR")
                cur.execute(f"ALTER TABLE auth.{table} ADD COLUMN {col['name']} {db_type}")
    finally:
        cur.close()

    _ensured_tables.add(table)


def get_auth(con: duckdb.DuckDBPyConnection, auth_cls: type) -> dict[str, Any] | None:
    """Read the single auth row. Returns None if not set."""
    ensure_auth_table(con, auth_cls)
    table = auth_cls.__table__
    cols = [f.name for f in dataclasses.fields(auth_cls)]
    col_list = ", ".join(cols)
    cur = con.cursor()
    try:
        row = cur.execute(f"SELECT {col_list} FROM auth.{table} LIMIT 1").fetchone()
    finally:
        cur.close()
    if row is None:
        return None
    return dict(zip(cols, row))


def get_auth_value(con: duckdb.DuckDBPyConnection, auth_cls: type, key: str) -> Any | None:
    """Read a single auth value by key."""
    row = get_auth(con, auth_cls)
    if row is None:
        return None
    return row.get(key)


def set_auth(con: duckdb.DuckDBPyConnection, auth_cls: type, **kwargs: Any) -> None:
    """Set auth values. Creates or updates the single auth row."""
    ensure_auth_table(con, auth_cls)
    table = auth_cls.__table__

    existing = get_auth(con, auth_cls)
    if existing:
        # Merge with existing values
        merged = {**existing, **kwargs}
    else:
        # Start from dataclass defaults
        defaults = {}
        for f in dataclasses.fields(auth_cls):
            if f.default is not dataclasses.MISSING:
                defaults[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                defaults[f.name] = f.default_factory()
            else:
                defaults[f.name] = None
        merged = {**defaults, **kwargs}

    cols = [f.name for f in dataclasses.fields(auth_cls)]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    values = [merged.get(c) for c in cols]
    cur = con.cursor()
    try:
        cur.execute(f"DELETE FROM auth.{table}")
        cur.execute(f"INSERT INTO auth.{table} ({col_names}) VALUES ({placeholders})", values)
    finally:
        cur.close()


def delete_auth(con: duckdb.DuckDBPyConnection, auth_cls: type) -> None:
    """Delete all auth for a package."""
    ensure_auth_table(con, auth_cls)
    table = auth_cls.__table__
    cur = con.cursor()
    try:
        cur.execute(f"DELETE FROM auth.{table}")
    finally:
        cur.close()


def auth_metadata(auth_cls: type) -> dict[str, Any]:
    """Return full metadata for an auth class, suitable for frontend UI generation."""
    return table_metadata(auth_cls)
