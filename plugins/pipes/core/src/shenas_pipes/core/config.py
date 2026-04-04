"""Config storage in the encrypted DuckDB using typed dataclass tables.

Each pipe/schema/component defines a config dataclass (same pattern as
canonical metric tables). The system creates a table per config class in
the `config` schema, with full type information and metadata available
for frontend UI generation via introspection.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import duckdb

from shenas_schemas.core.ddl import generate_ddl
from shenas_schemas.core.introspect import table_metadata


_ensured_tables: set[str] = set()


def ensure_config_table(con: duckdb.DuckDBPyConnection, config_cls: type) -> None:
    """Create the config schema and table if they don't exist, and add missing columns."""
    table = config_cls.__table__
    if table in _ensured_tables:
        return

    from shenas_schemas.core.introspect import table_metadata

    cur = con.cursor()
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS config")
        ddl = generate_ddl(config_cls).replace("metrics.", "config.")
        cur.execute(ddl)

        # Add any columns that exist in the dataclass but not yet in the table
        existing = {
            r[0]
            for r in cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'config' AND table_name = ?",
                [table],
            ).fetchall()
        }
        meta = table_metadata(config_cls)
        for col in meta["columns"]:
            if col["name"] not in existing:
                db_type = col.get("db_type", "VARCHAR")
                cur.execute(f"ALTER TABLE config.{table} ADD COLUMN {col['name']} {db_type}")
    finally:
        cur.close()

    _ensured_tables.add(table)


def get_config(con: duckdb.DuckDBPyConnection, config_cls: type) -> dict[str, Any] | None:
    """Read the single config row. Returns None if not set."""
    ensure_config_table(con, config_cls)
    table = config_cls.__table__
    cols = [f.name for f in dataclasses.fields(config_cls)]
    col_list = ", ".join(cols)
    cur = con.cursor()
    try:
        row = cur.execute(f"SELECT {col_list} FROM config.{table} LIMIT 1").fetchone()
    finally:
        cur.close()
    if row is None:
        return None
    return dict(zip(cols, row))


def get_config_value(con: duckdb.DuckDBPyConnection, config_cls: type, key: str) -> Any | None:
    """Read a single config value by key."""
    row = get_config(con, config_cls)
    if row is None:
        return None
    return row.get(key)


def set_config(con: duckdb.DuckDBPyConnection, config_cls: type, **kwargs: Any) -> None:
    """Set config values. Creates or updates the single config row."""
    ensure_config_table(con, config_cls)
    table = config_cls.__table__

    existing = get_config(con, config_cls)
    if existing:
        # Merge with existing values
        merged = {**existing, **kwargs}
    else:
        # Start from dataclass defaults
        defaults = {}
        for f in dataclasses.fields(config_cls):
            if f.default is not dataclasses.MISSING:
                defaults[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                defaults[f.name] = f.default_factory()
            else:
                defaults[f.name] = None
        merged = {**defaults, **kwargs}

    cols = [f.name for f in dataclasses.fields(config_cls)]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    values = [merged.get(c) for c in cols]
    cur = con.cursor()
    try:
        cur.execute(f"DELETE FROM config.{table}")
        cur.execute(f"INSERT INTO config.{table} ({col_names}) VALUES ({placeholders})", values)
    finally:
        cur.close()


def delete_config(con: duckdb.DuckDBPyConnection, config_cls: type) -> None:
    """Delete all config for a package."""
    ensure_config_table(con, config_cls)
    table = config_cls.__table__
    cur = con.cursor()
    try:
        cur.execute(f"DELETE FROM config.{table}")
    finally:
        cur.close()


def config_metadata(config_cls: type) -> dict[str, Any]:
    """Return full metadata for a config class, suitable for frontend UI generation."""
    return table_metadata(config_cls)
