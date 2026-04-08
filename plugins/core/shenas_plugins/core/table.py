"""Common Table ABC shared by sources and datasets.

This is the slim base class for any plugin-defined table that has a
schema (dataclass with ``Annotated[type, Field(...)]`` columns), a name,
a primary key, and an optional description. It carries no notion of
how the table is loaded or where its rows come from -- those concerns
belong to the source-side and dataset-side subclasses:

- ``shenas_sources.core.table.SourceTable`` (and its 7 kind subclasses)
  is the source layer: adds extract/dlt-resource/cursor/SCD2 machinery.
- ``shenas_datasets.core.table.MetricTable`` is the dataset layer: adds
  ``to_ddl()`` and is the future home of per-table transform classmethods.

The metadata ClassVars are prefixed ``table_*`` (``table_name``,
``table_display_name``, ``table_pk``, ``table_description``) so they
never collide with row-level columns called ``name``, ``description``,
``display_name``, etc. -- a real source of confusion in the previous
``__table__`` / ``__pk__`` dunder convention and the brief
``name``/``pk``/``description`` design.

Subclassing
-----------
Concrete subclasses just declare their schema fields and three required
ClassVars (``table_name``, ``table_display_name``, ``table_pk``). The
``@dataclass`` decorator is auto-applied via ``__init_subclass__``, so
subclasses don't need to write it explicitly. Abstract intermediate base
classes (like ``SourceTable``, ``MetricTable``, ``EventTable``, ...) opt
out of the dataclass + validation by setting
``_abstract: ClassVar[bool] = True`` in their class body.

Example (dataset side)
----------------------
::

    class DailyHRV(MetricTable):
        table_name = "daily_hrv"
        table_display_name = "Daily HRV"
        table_description = "One row per (date, source) heart-rate-variability summary."
        table_pk = ("date", "source")

        date: Annotated[str, Field(db_type="DATE", description="Calendar date")]
        source: Annotated[str, Field(db_type="VARCHAR", description="Data source")]
        rmssd: Annotated[float | None, Field(db_type="DOUBLE", description="...")] = None
"""

from __future__ import annotations

import dataclasses
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Sequence

    import duckdb


@dataclass(frozen=True)
class Field:
    """Structured metadata for schema fields and config fields.

    Used by canonical metric tables and pipe/component config tables alike.
    The frontend can introspect these to generate UIs on the fly.
    """

    db_type: str
    description: str
    unit: str | None = None
    value_range: tuple[float, float] | None = None
    example_value: float | str | None = None
    category: str | None = None  # "secret", "connection", "schedule", "wellbeing", etc.
    interpretation: str | None = None
    default: str | None = None  # default value (for config fields)
    db_default: str | None = None  # SQL DEFAULT expression (e.g. "current_timestamp", "'{}'")
    ui_widget: str | None = None  # "text", "number", "toggle", "password", "select", "textarea"
    options: tuple[str, ...] | None = None  # choices for select widgets


class Table:
    """Slim common base for source-side and dataset-side plugin tables.

    Required class attributes on every concrete subclass
    ----------------------------------------------------
    table_name           : table name (DuckDB ``<schema>.<table_name>``)
    table_display_name   : human-readable label for the frontend
    table_pk             : tuple of natural primary key column names

    Optional
    --------
    table_description    : free-text description (rendered in dashboards / docs)
    """

    table_name: ClassVar[str]
    table_display_name: ClassVar[str]
    table_pk: ClassVar[tuple[str, ...]]

    table_description: ClassVar[str | None] = None
    table_schema: ClassVar[str | None] = None

    # Cache of (schema, table_name) tuples that have already had their
    # CREATE TABLE + ALTER TABLE migrations applied this process. Read /
    # written by ``ensure``.
    _ensured: ClassVar[set[tuple[str, str]]] = set()

    # Internal: True on Table itself and on every abstract intermediate base
    # (SourceTable, MetricTable, EventTable, IntervalTable, ...). False on
    # concrete subclasses (set by ``__init_subclass__``). When ``_abstract`` is
    # True we skip the @dataclass decorator and the metadata validation.
    _abstract: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # If a subclass doesn't explicitly mark itself abstract, it's concrete.
        if "_abstract" not in cls.__dict__:
            cls._abstract = False
        if cls._abstract:
            return
        # Apply @dataclass to concrete subclasses so the field-annotation
        # syntax (`name: Annotated[type, Field(...)] = default`) just works.
        if "__dataclass_fields__" not in cls.__dict__:
            dataclass(cls)
        cls._validate()

    @classmethod
    def _validate(cls) -> None:
        """Raise TypeError if any required class attribute is missing.

        Subclasses extend this to enforce per-layer requirements (e.g.
        ``SourceTable`` requires ``kind``; ``IntervalTable`` requires
        ``time_start`` and ``time_end``).
        """
        for required in ("table_name", "table_display_name", "table_pk"):
            if not getattr(cls, required, None):
                msg = f"{cls.__name__}: missing required class attribute `{required}`"
                raise TypeError(msg)

    @classmethod
    def _finalize(cls) -> None:
        """Force-apply the @dataclass + validation that was deferred by an
        intermediate base class (e.g. ``SourceAuth`` / ``SourceConfig``,
        which keep subclasses abstract until ``table_name`` is set).
        """
        cls._abstract = False
        if "__dataclass_fields__" not in cls.__dict__:
            dataclass(cls)
        cls._validate()

    @classmethod
    def table_metadata(cls) -> dict[str, Any]:
        """Return structured metadata for this table.

        Walks the dataclass fields, extracts ``Field()`` metadata from
        each ``Annotated[type, Field(...)]`` hint, and returns a dict
        suitable for the frontend / LLM context. Used by
        :meth:`shenas_datasets.core.dataset.Dataset.metadata` and the
        per-source ``Source.get_*_metadata`` helpers.
        """
        import sys

        mod = sys.modules.get(cls.__module__, None)
        globalns = vars(mod) if mod else None
        hints: dict[str, Any] = get_type_hints(cls, globalns=globalns, include_extras=True)
        columns: list[dict[str, Any]] = []
        for f in dataclasses.fields(cls):
            col_meta = cls._extract_field_meta(hints[f.name])
            columns.append({"name": f.name, "nullable": f.name not in cls.table_pk, **col_meta})
        return {
            "table": cls.table_name,
            "description": getattr(cls, "table_description", None) or cls.__doc__,
            "primary_key": list(cls.table_pk),
            "columns": columns,
        }

    @classmethod
    def to_ddl(cls, *, schema: str = "metrics") -> str:
        """Render the ``CREATE TABLE IF NOT EXISTS <schema>.<table_name> (...)`` DDL.

        Walks the dataclass fields, maps each to a DuckDB column type via
        the ``db_type`` from its ``Field`` metadata (or the type-map for
        bare ``str``/``int``/``float`` annotations), and emits a complete
        ``CREATE TABLE`` statement with a composite ``PRIMARY KEY`` clause.
        """
        hints: dict[str, type] = get_type_hints(cls, include_extras=True)
        lines: list[str] = []
        for f in dataclasses.fields(cls):
            col_type = cls._duckdb_type(hints[f.name])
            not_null = " NOT NULL" if f.name in cls.table_pk else ""
            db_default = ""
            meta = cls._get_field_obj(hints[f.name])
            if meta and meta.db_default:
                db_default = f" DEFAULT {meta.db_default}"
            lines.append(f"    {f.name} {col_type}{not_null}{db_default}")
        lines.append(f"    PRIMARY KEY ({', '.join(cls.table_pk)})")
        return f"CREATE TABLE IF NOT EXISTS {schema}.{cls.table_name} (\n" + ",\n".join(lines) + "\n)"

    @classmethod
    def ensure(cls, con: duckdb.DuckDBPyConnection, *, schema: str = "metrics") -> None:
        """Create this table in ``schema`` if missing, then add any new columns.

        Caller is responsible for ensuring the schema itself exists -- use
        :func:`ensure_schema` for the orchestrated multi-table version.
        """
        con.execute(cls.to_ddl(schema=schema))
        cls._add_missing_columns(con, schema=schema)

    @classmethod
    def _add_missing_columns(cls, con: duckdb.DuckDBPyConnection, *, schema: str = "metrics") -> None:
        """Add columns that exist on the dataclass but not in the live DuckDB table."""
        hints: dict[str, type] = get_type_hints(cls, include_extras=True)
        existing = {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
                [schema, cls.table_name],
            ).fetchall()
        }
        for f in dataclasses.fields(cls):
            if f.name not in existing:
                col_type = cls._duckdb_type(hints[f.name])
                con.execute(f"ALTER TABLE {schema}.{cls.table_name} ADD COLUMN {f.name} {col_type}")

    # ------------------------------------------------------------------
    # Single-row CRUD (replaces the old TableStore wrapper)
    # ------------------------------------------------------------------

    @classmethod
    def _resolve_schema(cls, schema: str | None) -> str:
        s = schema or cls.table_schema
        if not s:
            msg = f"{cls.__name__}: no schema specified and no `table_schema` ClassVar set on the class or its bases"
            raise TypeError(msg)
        return s

    @classmethod
    def _ensure_once(cls, schema: str) -> None:
        """Idempotent CREATE SCHEMA + CREATE TABLE; memoized per process."""
        key = (schema, cls.table_name)
        if key in cls._ensured:
            return
        from app.db import cursor

        with cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            cls.ensure(cur, schema=schema)
        cls._ensured.add(key)

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        """Read the single row from this table as a dict, or None if empty."""
        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)
        cols = [f.name for f in dataclasses.fields(cls)]
        col_list = ", ".join(cols)
        with cursor() as cur:
            row = cur.execute(f"SELECT {col_list} FROM {s}.{cls.table_name} LIMIT 1").fetchone()
        if row is None:
            return None
        return dict(zip(cols, row, strict=False))

    @classmethod
    def read_value(cls, key: str, *, schema: str | None = None) -> Any | None:
        """Read a single column value from the row, or None."""
        row = cls.read_row(schema=schema)
        if row is None:
            return None
        return row.get(key)

    @classmethod
    def write_row(cls, *, schema: str | None = None, **kwargs: Any) -> None:
        """Upsert the single row: merge with existing values, then DELETE + INSERT."""
        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)

        existing = cls.read_row(schema=s)
        if existing:
            merged = {**existing, **kwargs}
        else:
            defaults: dict[str, Any] = {}
            for f in dataclasses.fields(cls):
                if f.default is not dataclasses.MISSING:
                    defaults[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
                    defaults[f.name] = f.default_factory()  # type: ignore[misc]
                else:
                    defaults[f.name] = None
            merged = {**defaults, **kwargs}

        cols = [f.name for f in dataclasses.fields(cls)]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        values = [merged.get(c) for c in cols]
        with cursor() as cur:
            cur.execute(f"DELETE FROM {s}.{cls.table_name}")
            cur.execute(f"INSERT INTO {s}.{cls.table_name} ({col_names}) VALUES ({placeholders})", values)

    @classmethod
    def clear_rows(cls, *, schema: str | None = None) -> None:
        """Delete every row from this table."""
        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)
        with cursor() as cur:
            cur.execute(f"DELETE FROM {s}.{cls.table_name}")

    # ------------------------------------------------------------------
    # Schema-introspection / DDL helpers (used internally by to_ddl,
    # ensure, table_metadata, and SourceTable.to_dlt_columns)
    # ------------------------------------------------------------------

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
            return Table._duckdb_type(inner[0])
        if hint in Table._DUCKDB_TYPE_MAP:
            return Table._DUCKDB_TYPE_MAP[hint]
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
                    result = Table._get_field_obj(arg)
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
            return Table._extract_field_meta(inner[0])
        return {}

    @staticmethod
    def ensure_schema(con: duckdb.DuckDBPyConnection, all_tables: Sequence[type[Table]], *, schema: str = "metrics") -> None:
        """Create the named schema and ensure every table in ``all_tables`` exists.

        Also adds any columns that exist on the dataclass but not in the live
        DuckDB table (forward-compatible schema migration).
        """
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for t in all_tables:
            t.ensure(con, schema=schema)
