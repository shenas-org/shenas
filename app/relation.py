"""Relation: read-only base for any DuckDB-backed typed row class.

Provides the ``_Meta`` machinery, auto-``@dataclass`` via
``__init_subclass__``, column introspection, and generic read methods
(``find``, ``all``, ``from_row``). Does NOT own DDL or write
operations -- those live on :class:`app.table.Table` (for physical
tables) and are absent from :class:`app.view.View` (read-only).

The ``Relation -> Table | View`` split means JOINs materialised as
DuckDB VIEWs get the same typed, ORM-accessible interface as physical
tables, without inheriting insert/delete/DDL.
"""

from __future__ import annotations

import dataclasses
import types
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Self, get_args, get_origin, get_type_hints


@dataclass(frozen=True)
class Field:
    """Structured metadata for schema fields and config fields."""

    db_type: str
    description: str
    display_name: str | None = None
    unit: str | None = None
    value_range: tuple[float, float] | None = None
    example_value: float | str | None = None
    category: str | None = None
    interpretation: str | None = None
    default: str | None = None
    db_default: str | None = None
    ui_widget: str | None = None
    options: tuple[str, ...] | None = None


class Relation:
    """Read-only base for any DuckDB-backed typed row class.

    Provides the ``_Meta`` machinery, auto-``@dataclass`` via
    ``__init_subclass__``, column introspection, and generic read
    methods (``find``, ``all``, ``from_row``).
    """

    class _Meta:
        name: ClassVar[str]
        display_name: ClassVar[str]
        pk: ClassVar[tuple[str, ...]] = ()
        description: ClassVar[str | None] = None
        schema: ClassVar[str | None] = None
        database: ClassVar[str] = "user"

    _abstract: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "_Meta" in cls.__dict__:
            local_meta = cls.__dict__["_Meta"]
            parent_meta: type | None = None
            for base in cls.__mro__[1:]:
                if "_Meta" in base.__dict__:
                    parent_meta = base.__dict__["_Meta"]
                    break
            if parent_meta is not None and parent_meta not in local_meta.__mro__:
                cls._Meta = type(  # ty: ignore[invalid-assignment]
                    "_Meta",
                    (local_meta, parent_meta),
                    {k: v for k, v in vars(local_meta).items() if not k.startswith("__")},
                )
        if "_abstract" not in cls.__dict__:
            cls._abstract = False
        if cls._abstract:
            return
        if "__dataclass_fields__" not in cls.__dict__:
            dataclass(cls)
        cls._validate()

    @classmethod
    def _validate(cls) -> None:
        """Raise TypeError if ``_Meta`` is missing required attributes.

        ``Relation`` requires only ``name`` and ``display_name``.
        ``Table`` overrides to additionally require ``pk``.
        """
        if cls._Meta is Relation._Meta:
            msg = f"{cls.__name__}: must define an inner `_Meta` class"
            raise TypeError(msg)
        for required in ("name", "display_name"):
            if not getattr(cls._Meta, required, None):
                msg = f"{cls.__name__}: _Meta missing required attribute `{required}`"
                raise TypeError(msg)

    @classmethod
    def _finalize(cls) -> None:
        """Force-apply the @dataclass + validation (deferred by intermediate bases)."""
        cls._abstract = False
        if "__dataclass_fields__" not in cls.__dict__:
            dataclass(cls)
        cls._validate()

    # ------------------------------------------------------------------
    # Column introspection
    # ------------------------------------------------------------------

    @classmethod
    def column_metadata(cls) -> list[dict[str, Any]]:
        """Return the list of column metadata dicts."""
        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)
        return [
            {
                "name": f.name,
                "nullable": f.name not in cls._Meta.pk,
                **cls._extract_field_meta(hints[f.name]),
            }
            for f in dataclasses.fields(cls)
        ]

    _DUCKDB_TYPE_MAP: ClassVar[dict[type, str]] = {
        str: "VARCHAR",
        int: "INTEGER",
        float: "DOUBLE",
    }

    @staticmethod
    def _duckdb_type(hint: type) -> str:
        """Resolve the DuckDB SQL type for an ``Annotated[T, Field(...)]`` hint."""
        origin = get_origin(hint)
        if origin is Annotated:
            meta = get_args(hint)[1]
            if isinstance(meta, Field):
                return meta.db_type
            return meta
        if origin is types.UnionType or str(origin) == "typing.Union":
            inner = [a for a in get_args(hint) if a is not type(None)]
            return Relation._duckdb_type(inner[0])
        if hint in Relation._DUCKDB_TYPE_MAP:
            return Relation._DUCKDB_TYPE_MAP[hint]
        msg = f"No DuckDB mapping for {hint}"
        raise ValueError(msg)

    @staticmethod
    def _get_field_obj(hint: type) -> Field | None:
        """Extract a ``Field`` from an ``Annotated[T, Field(...)]`` hint."""
        origin = get_origin(hint)
        if origin is Annotated:
            meta = get_args(hint)[1]
            if isinstance(meta, Field):
                return meta
        if origin is types.UnionType or str(origin) == "typing.Union":
            for arg in get_args(hint):
                if arg is not type(None):
                    result = Relation._get_field_obj(arg)
                    if result:
                        return result
        return None

    @staticmethod
    def _extract_field_meta(hint: type) -> dict[str, Any]:
        """Extract Field metadata as a dict from an ``Annotated[T, Field(...)]`` hint."""
        origin = get_origin(hint)
        if origin is Annotated:
            meta = get_args(hint)[1]
            if isinstance(meta, Field):
                return {k: v for k, v in dataclasses.asdict(meta).items() if v is not None}
            return {"db_type": meta}
        if origin is types.UnionType or str(origin) == "typing.Union":
            inner = [a for a in get_args(hint) if a is not type(None)]
            return Relation._extract_field_meta(inner[0])
        return {}

    # ------------------------------------------------------------------
    # Read-only CRUD (qualified name, column names, from_row, find, all)
    # ------------------------------------------------------------------

    @classmethod
    def _resolve_schema(cls, schema: str | None) -> str:
        s = schema or cls._Meta.schema
        if not s:
            msg = f"{cls.__name__}: no schema specified and no schema set on _Meta"
            raise TypeError(msg)
        return s

    @classmethod
    def _resolve_database(cls) -> str | None:
        if getattr(cls._Meta, "database", "user") == "system":
            return "shenas"
        return None

    @classmethod
    def _qualified(cls) -> str:
        return f"{cls._resolve_schema(None)}.{cls._Meta.name}"

    @classmethod
    def _column_names(cls) -> list[str]:
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_row(cls, row: tuple[Any, ...]) -> Self:
        """Build an instance from a row tuple in dataclass field order."""
        return cls(**dict(zip(cls._column_names(), row, strict=True)))

    @classmethod
    def find(cls, *pk_values: Any) -> Self | None:
        """Look up a single row by its primary key. Returns ``None`` if missing."""
        from app.database import cursor

        if len(pk_values) != len(cls._Meta.pk):
            msg = f"{cls.__name__}.find expects {len(cls._Meta.pk)} pk value(s), got {len(pk_values)}"
            raise TypeError(msg)

        cols = ", ".join(cls._column_names())
        where = " AND ".join(f"{c} = ?" for c in cls._Meta.pk)
        with cursor(database=cls._resolve_database()) as cur:
            row = cur.execute(f"SELECT {cols} FROM {cls._qualified()} WHERE {where}", list(pk_values)).fetchone()
        return cls.from_row(row) if row else None

    @classmethod
    def all(
        cls,
        *,
        where: str | None = None,
        params: list[Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        as_of: str | None = None,
        include_history: bool = False,
    ) -> list[Self]:
        """Return every row matching the optional WHERE clause as instances.

        For SCD2 tables: automatically filters to the current slice unless
        *as_of* is provided or *include_history* is True.
        """
        from app.database import cursor

        clauses: list[str] = []
        scd2_clause: str | None = None
        scd2_fn = getattr(cls, "scd2_filter", None)
        if scd2_fn is not None and not include_history:
            scd2_clause = scd2_fn(as_of=as_of) or None
            if scd2_clause:
                clauses.append(scd2_clause)
        if where:
            clauses.append(where)

        cols = ", ".join(cls._column_names())
        base = f"SELECT {cols} FROM {cls._qualified()}"

        def _build_sql(extra_clauses: list[str]) -> str:
            sql = base
            if extra_clauses:
                sql += f" WHERE {' AND '.join(extra_clauses)}"
            if order_by:
                sql += f" ORDER BY {order_by}"
            if limit is not None:
                sql += f" LIMIT {int(limit)}"
            return sql

        with cursor(database=cls._resolve_database()) as cur:
            try:
                rows = cur.execute(_build_sql(clauses), params or []).fetchall()
            except Exception:
                # SCD2 columns (_dlt_valid_to) may not exist before the first
                # dlt sync. Retry without the auto-injected SCD2 filter.
                if scd2_clause:
                    fallback = [c for c in clauses if c != scd2_clause]
                    rows = cur.execute(_build_sql(fallback), params or []).fetchall()
                else:
                    raise
        return [cls.from_row(r) for r in rows]
