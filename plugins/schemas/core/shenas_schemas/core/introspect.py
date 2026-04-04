"""Extract structured metadata from canonical schema dataclasses."""

from __future__ import annotations

import dataclasses
import types
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from shenas_schemas.core.field import Field


def _extract_field_meta(hint: type) -> dict[str, Any]:
    origin = get_origin(hint)
    if origin is Annotated:
        meta = get_args(hint)[1]
        if isinstance(meta, Field):
            return {k: v for k, v in dataclasses.asdict(meta).items() if v is not None}
        return {"db_type": meta}
    if origin is types.UnionType or str(origin) == "typing.Union":
        inner = [a for a in get_args(hint) if a is not type(None)]
        return _extract_field_meta(inner[0])
    return {}


def table_metadata(cls: type) -> dict[str, Any]:
    """Return full metadata for a table class, suitable for LLM context."""
    import sys

    mod = sys.modules.get(cls.__module__, None)
    globalns = vars(mod) if mod else None
    hints: dict[str, Any] = get_type_hints(cls, globalns=globalns, include_extras=True)
    columns: list[dict[str, Any]] = []
    for f in dataclasses.fields(cls):
        meta = _extract_field_meta(hints[f.name])
        columns.append({"name": f.name, "nullable": f.name not in cls.__pk__, **meta})
    return {
        "table": cls.__table__,
        "description": cls.__doc__,
        "primary_key": list(cls.__pk__),
        "columns": columns,
    }


def schema_metadata(all_tables: list[type]) -> list[dict[str, Any]]:
    """Return metadata for all canonical tables."""
    return [table_metadata(cls) for cls in all_tables]
