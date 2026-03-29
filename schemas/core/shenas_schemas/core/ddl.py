from __future__ import annotations

import dataclasses
import types
from typing import Annotated, get_args, get_origin, get_type_hints

import duckdb

from shenas_schemas.core.field import Field

_TYPE_MAP: dict[type, str] = {
    str: "VARCHAR",
    int: "INTEGER",
    float: "DOUBLE",
}


def _duckdb_type(hint: type) -> str:
    origin = get_origin(hint)
    if origin is Annotated:
        meta = get_args(hint)[1]
        if isinstance(meta, Field):
            return meta.db_type
        return meta
    if origin is types.UnionType or str(origin) == "typing.Union":
        inner = [a for a in get_args(hint) if a is not type(None)]
        return _duckdb_type(inner[0])
    if hint in _TYPE_MAP:
        return _TYPE_MAP[hint]
    raise ValueError(f"No DuckDB mapping for {hint}")


def generate_ddl(cls: type) -> str:
    """Generate CREATE TABLE DDL from a dataclass with __table__ and __pk__."""
    table: str = cls.__table__
    pk: tuple[str, ...] = cls.__pk__
    hints: dict[str, type] = get_type_hints(cls, include_extras=True)
    lines: list[str] = []
    for f in dataclasses.fields(cls):
        col_type = _duckdb_type(hints[f.name])
        not_null = " NOT NULL" if f.name in pk else ""
        lines.append(f"    {f.name} {col_type}{not_null}")
    lines.append(f"    PRIMARY KEY ({', '.join(pk)})")
    return f"CREATE TABLE IF NOT EXISTS metrics.{table} (\n" + ",\n".join(lines) + "\n)"


def ensure_schema(con: duckdb.DuckDBPyConnection, all_tables: list[type]) -> None:
    """Create the metrics schema and all tables from the given dataclass list."""
    con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
    for cls in all_tables:
        con.execute(generate_ddl(cls))
