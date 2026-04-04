"""Convert table dataclasses to dlt column definitions."""

from __future__ import annotations

import dataclasses
from typing import Any, get_type_hints

from shenas_schemas.core.ddl import _duckdb_type, _get_field_obj

# Map DuckDB types to dlt's type system
_DLT_TYPE_MAP: dict[str, str] = {
    "varchar": "text",
    "text": "text",
    "integer": "bigint",
    "bigint": "bigint",
    "double": "double",
    "float": "double",
    "real": "double",
    "boolean": "bool",
    "date": "date",
    "timestamp": "timestamp",
    "time": "time",
    "json": "json",
    "blob": "binary",
}


def dataclass_to_dlt_columns(cls: type) -> dict[str, dict[str, Any]]:
    """Convert a table dataclass with Field annotations to dlt column schema.

    Returns a dict suitable for passing to @dlt.resource(columns=...).
    """
    hints = get_type_hints(cls, include_extras=True)
    columns: dict[str, dict[str, Any]] = {}
    for f in dataclasses.fields(cls):
        if f.name.startswith("_"):
            continue
        hint = hints[f.name]
        db_type = _duckdb_type(hint).lower()
        dlt_type = _DLT_TYPE_MAP.get(db_type, "text")
        col: dict[str, Any] = {"name": f.name, "data_type": dlt_type}

        meta = _get_field_obj(hint)
        if meta and meta.description:
            col["description"] = meta.description

        columns[f.name] = col
    return columns
