"""Auto-derive @strawberry.type from Table subclasses.

Generates a Strawberry GraphQL type from a Table/Relation's dataclass
fields and _Meta, so the schema definition lives in one place (the
Python class) instead of being duplicated in a hand-written
@strawberry.type.

Usage::

    from app.graphql.derive import gql_type_from_table
    from app.entity import Entity, EntityType

    GqlEntity = gql_type_from_table(Entity, name="GqlEntity")
    GqlEntityType = gql_type_from_table(EntityType, name="EntityTypeType")
"""

from __future__ import annotations

import dataclasses
from typing import Annotated, Any, Optional, get_args, get_origin, get_type_hints

import strawberry

from app.relation import Field

# Map DuckDB column types to Python types for GraphQL scalars.
_DB_TYPE_MAP: dict[str, type | Any] = {
    "varchar": str,
    "text": str,
    "integer": int,
    "bigint": int,
    "double": float,
    "float": float,
    "real": float,
    "boolean": bool,
    "date": str,
    "timestamp": str,
    "time": str,
    "json": strawberry.scalars.JSON,
}


def _resolve_python_type(hint: Any, field_meta: Field | None) -> Any:
    """Determine the GraphQL-facing Python type for a dataclass field.

    Priority:
    1. If ``field_meta.db_type`` is set, map it via ``_DB_TYPE_MAP``.
    2. Otherwise, use the raw type hint.

    Handles ``Optional[T]`` / ``T | None`` by wrapping in ``Optional``.
    """
    # Check if the type hint is Optional (T | None)
    is_optional = False
    origin = get_origin(hint)
    args = get_args(hint)

    # Strip Annotated wrapper
    if origin is Annotated:
        hint = args[0]
        origin = get_origin(hint)
        args = get_args(hint)

    # Check for Union with None (Optional) -- handles both
    # types.UnionType (T | None) and typing.Union (Optional[T]).
    import typing

    if origin is type(int | str) or origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args:
            is_optional = True
            hint = non_none[0]
            origin = get_origin(hint)
            args = get_args(hint)

    # Strip Annotated again (handles Optional[Annotated[T, ...]])
    if origin is Annotated:
        hint = args[0]
        origin = get_origin(hint)
        args = get_args(hint)

    # Resolve from db_type if available
    if field_meta and field_meta.db_type:
        base = _DB_TYPE_MAP.get(field_meta.db_type.lower(), str)
    else:
        base = hint if isinstance(hint, type) else str

    if is_optional:
        return base | None
    return base


def _get_field_meta(hint: Any) -> Field | None:
    """Extract the Field metadata from an Annotated type hint.

    Handles both ``Annotated[T, Field(...)]`` and
    ``Optional[Annotated[T, Field(...)]]`` (i.e. ``Annotated[T, ...] | None``).
    """
    origin = get_origin(hint)
    args = get_args(hint)
    # Unwrap Optional/Union to find the Annotated inner type.
    import typing

    if (origin is type(int | str) or origin is typing.Union) and args:
        for arg in args:
            if arg is not type(None) and get_origin(arg) is Annotated:
                hint = arg
                break
    if get_origin(hint) is not Annotated:
        return None
    for arg in get_args(hint)[1:]:
        if isinstance(arg, Field):
            return arg
    return None


def gql_type_from_table(
    table_cls: type,
    *,
    name: str | None = None,
    exclude: set[str] | None = None,
    overrides: dict[str, tuple[Any, Any]] | None = None,
) -> Any:
    """Generate a @strawberry.type from a Table/Relation subclass.

    Parameters
    ----------
    table_cls
        The Table or Relation subclass to derive from.
    name
        GraphQL type name. Defaults to the class name.
    exclude
        Field names to omit (e.g. ``{"id"}`` for auto-PK fields).
    overrides
        Additional or replacement fields. Mapping of
        ``field_name -> (type, value)`` where *value* is either:

        - a callable (resolver function) -- becomes a ``@strawberry.field``
        - any other value -- used as the default (e.g. ``None``).

    Returns
    -------
    type
        A ``@strawberry.type``-decorated class with fields matching
        the Table's dataclass fields.
    """
    if exclude is None:
        exclude = set()
    if overrides is None:
        overrides = {}
    # Always exclude internal dlt fields
    exclude = exclude | {"_dlt_valid_from", "_dlt_valid_to", "_dlt_id", "_dlt_load_id"}
    # Also exclude any fields that overrides will replace
    exclude = exclude | set(overrides.keys())

    type_name = name or table_cls.__name__
    hints = get_type_hints(table_cls, include_extras=True)
    dc_fields = dataclasses.fields(table_cls)

    annotations: dict[str, Any] = {}
    namespace: dict[str, Any] = {}

    for f in dc_fields:
        if f.name in exclude or f.name.startswith("_"):
            continue
        hint = hints.get(f.name, str)
        field_meta = _get_field_meta(hint)
        py_type = _resolve_python_type(hint, field_meta)
        annotations[f.name] = py_type

        # Set default value
        if f.default is not dataclasses.MISSING:
            namespace[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:
            namespace[f.name] = strawberry.field(default_factory=f.default_factory)
        elif py_type is Optional or (get_origin(py_type) and type(None) in get_args(py_type)):
            namespace[f.name] = None
        # else: required field, no default

    # Apply overrides (resolver functions or typed defaults).
    for field_name, (field_type, value) in overrides.items():
        annotations[field_name] = field_type
        if isinstance(value, strawberry.types.field.StrawberryField):
            # Already a strawberry.field() descriptor -- use as-is
            namespace[field_name] = value
        elif callable(value) and not isinstance(value, type):
            namespace[field_name] = strawberry.field(resolver=value)
        else:
            namespace[field_name] = value

    namespace["__annotations__"] = annotations

    # Get description from _Meta
    description = getattr(getattr(table_cls, "_Meta", None), "description", "") or ""

    # Build the class
    cls = type(type_name, (), namespace)
    return strawberry.type(description=description)(cls)
