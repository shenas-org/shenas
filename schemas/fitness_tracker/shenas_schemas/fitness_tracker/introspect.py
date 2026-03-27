"""Extract structured metadata from canonical schema dataclasses."""

import dataclasses
import types
from typing import Annotated, get_args, get_origin, get_type_hints

from shenas_schemas.fitness_tracker.field import Field
from shenas_schemas.fitness_tracker.metrics import ALL_TABLES


def _extract_field_meta(hint) -> dict:
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


def table_metadata(cls) -> dict:
    """Return full metadata for a table class, suitable for LLM context."""
    hints = get_type_hints(cls, include_extras=True)
    columns = []
    for f in dataclasses.fields(cls):
        meta = _extract_field_meta(hints[f.name])
        columns.append({"name": f.name, "nullable": f.name not in cls.__pk__, **meta})
    return {
        "table": cls.__table__,
        "description": cls.__doc__,
        "primary_key": list(cls.__pk__),
        "columns": columns,
    }


def schema_metadata() -> list[dict]:
    """Return metadata for all canonical tables."""
    return [table_metadata(cls) for cls in ALL_TABLES]
