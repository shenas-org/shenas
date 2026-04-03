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


def ensure_config_table(con: duckdb.DuckDBPyConnection, config_cls: type) -> None:
    """Create the config schema and the config table if they don't exist."""
    con.execute("CREATE SCHEMA IF NOT EXISTS config")
    ddl = generate_ddl(config_cls).replace("metrics.", "config.")
    con.execute(ddl)


def get_config(con: duckdb.DuckDBPyConnection, config_cls: type) -> dict[str, Any] | None:
    """Read the single config row. Returns None if not set."""
    ensure_config_table(con, config_cls)
    table = config_cls.__table__
    cols = [f.name for f in dataclasses.fields(config_cls)]
    col_list = ", ".join(cols)
    row = con.execute(f"SELECT {col_list} FROM config.{table} LIMIT 1").fetchone()
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

    con.execute(f"DELETE FROM config.{table}")
    cols = [f.name for f in dataclasses.fields(config_cls)]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    values = [merged.get(c) for c in cols]
    con.execute(f"INSERT INTO config.{table} ({col_names}) VALUES ({placeholders})", values)


def delete_config(con: duckdb.DuckDBPyConnection, config_cls: type) -> None:
    """Delete all config for a package."""
    ensure_config_table(con, config_cls)
    table = config_cls.__table__
    con.execute(f"DELETE FROM config.{table}")


def config_metadata(config_cls: type) -> dict[str, Any]:
    """Return full metadata for a config class, suitable for frontend UI generation."""
    return table_metadata(config_cls)
