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

import contextlib
import dataclasses
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Self, get_args, get_origin, get_type_hints

import duckdb

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class Field:
    """Structured metadata for schema fields and config fields.

    Used by canonical metric tables and pipe/component config tables alike.
    The frontend can introspect these to generate UIs on the fly.
    """

    db_type: str
    description: str
    display_name: str | None = None
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

    Every concrete subclass declares an inner ``_Meta`` class holding
    the table's identity. Putting these on a nested class (rather than
    on the subclass itself) keeps them clear of the row-level dataclass
    fields -- a real source of confusion in earlier designs where row
    columns called ``name`` / ``description`` collided with the table's
    own metadata.

    Required attributes on every concrete subclass's ``_Meta``
    ---------------------------------------------------------
    name           : table name (DuckDB ``<schema>.<name>``)
    display_name   : human-readable label for the frontend
    pk             : tuple of natural primary key column names

    Optional
    --------
    description    : free-text description (rendered in dashboards / docs)
    schema         : default DuckDB schema for this table
    """

    class _Meta:
        # Marker base; concrete subclasses MUST override _Meta with all
        # required attributes. Defaults are read from this base when a
        # subclass omits the optional ones.
        name: ClassVar[str]
        display_name: ClassVar[str]
        pk: ClassVar[tuple[str, ...]]
        description: ClassVar[str | None] = None
        schema: ClassVar[str | None] = None

    # Per-user data isolation: each Table subclass declares which
    # logical database it lives in. ``"system"`` = the device-wide
    # registry DB (local_users, plugin install state, etc.).
    # ``"user"`` = the current user's encrypted DB (workspace,
    # hotkeys, source data, metrics, hypotheses). The default is
    # ``"user"`` because the vast majority of tables are user-scoped;
    # system tables explicitly opt in. Resolved at query time via
    # :meth:`_resolve_database`.
    database: ClassVar[str] = "user"

    # Internal: True on Table itself and on every abstract intermediate base
    # (SourceTable, MetricTable, EventTable, IntervalTable, ...). False on
    # concrete subclasses (set by ``__init_subclass__``). When ``_abstract`` is
    # True we skip the @dataclass decorator and the metadata validation.
    _abstract: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Re-bind a locally-declared `_Meta` to inherit from the nearest
        # parent class's `_Meta`, so attributes defined on intermediate
        # bases (e.g. `_DailyAggregate._Meta.pk`) flow into concrete
        # leaf subclasses without each leaf having to repeat them.
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
        """Raise TypeError if ``_Meta`` is missing required attributes.

        Subclasses extend this to enforce per-layer requirements (e.g.
        ``SourceTable`` requires ``kind``; ``IntervalTable`` requires
        ``time_start`` and ``time_end``).
        """
        if cls._Meta is Table._Meta:
            msg = f"{cls.__name__}: must define an inner `_Meta` class"
            raise TypeError(msg)
        for required in ("name", "display_name", "pk"):
            if not getattr(cls._Meta, required, None):
                msg = f"{cls.__name__}: _Meta missing required attribute `{required}`"
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
    def column_metadata(cls) -> list[dict[str, Any]]:
        """Return the list of column metadata dicts for this table.

        Walks the dataclass fields, extracts ``Field()`` metadata from each
        ``Annotated[type, Field(...)]`` hint. Used by system tables
        (SourceAuth / SourceConfig / SingletonTable subclasses) that need
        column-level UI/introspection but don't have a data-table kind.
        Data tables use :meth:`DataTable.table_metadata` which composes
        this with identity + kind + time_columns + as_of_macro.
        """
        # Don't pass `globalns=` here. ``get_type_hints`` walks the MRO and
        # resolves each base class's annotations against THAT base's own
        # ``__module__``, which is what we want -- ``ClassVar`` (and other
        # typing imports) live in whichever file declared them, not
        # necessarily in the leaf subclass's module. Forcing
        # ``globalns=vars(leaf_module)`` makes intermediate-base annotations
        # like ``SingletonTable._abstract: ClassVar[bool]`` resolve in the
        # leaf's namespace, which often doesn't import ``ClassVar`` and
        # crashes with a NameError at request time.
        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)
        return [
            {
                "name": f.name,
                "nullable": f.name not in cls._Meta.pk,
                **cls._extract_field_meta(hints[f.name]),
            }
            for f in dataclasses.fields(cls)
        ]

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
            not_null = " NOT NULL" if f.name in cls._Meta.pk else ""
            db_default = ""
            meta = cls._get_field_obj(hints[f.name])
            if meta and meta.db_default:
                db_default = f" DEFAULT {meta.db_default}"
            lines.append(f'    "{f.name}" {col_type}{not_null}{db_default}')
        pk_cols = ", ".join(f'"{c}"' for c in cls._Meta.pk)
        lines.append(f"    PRIMARY KEY ({pk_cols})")
        return f'CREATE TABLE IF NOT EXISTS "{schema}"."{cls._Meta.name}" (\n' + ",\n".join(lines) + "\n)"

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
                [schema, cls._Meta.name],
            ).fetchall()
        }
        for f in dataclasses.fields(cls):
            if f.name not in existing:
                col_type = cls._duckdb_type(hints[f.name])
                with contextlib.suppress(duckdb.CatalogException):
                    con.execute(f'ALTER TABLE "{schema}"."{cls._Meta.name}" ADD COLUMN "{f.name}" {col_type}')

    @classmethod
    def _resolve_schema(cls, schema: str | None) -> str:
        s = schema or cls._Meta.schema
        if not s:
            msg = f"{cls.__name__}: no schema specified and no `table_schema` ClassVar set on the class or its bases"
            raise TypeError(msg)
        return s

    @classmethod
    def _resolve_database(cls) -> str | None:
        """Return the ATTACH alias the cursor should USE for this table.

        ``"system"`` for tables marked ``database = "system"`` (the
        device-wide registry: local users, sessions, plugin install
        state). ``f"user_{<current user id>}"`` for everything else.

        The current user id comes from the ``current_user_id``
        contextvar set by the request middleware. In single-user mode
        the contextvar defaults to 0, so user-scoped tables resolve to
        ``user_0`` and the same code path covers both modes.
        """
        if cls.database == "system":
            return "shenas"
        return None

    # ------------------------------------------------------------------
    # Multi-row CRUD (find / all / insert / save / delete)
    #
    # Generic primitives that operate on the dataclass fields directly,
    # so subclasses don't need a wrapper class with hand-written SQL.
    # The schema is resolved from ``table_schema``; the column list is
    # taken from ``dataclasses.fields(cls)`` in declaration order, which
    # matches the DDL emitted by ``to_ddl`` and therefore matches both
    # SELECT-by-column-name and ``RETURNING *`` row order.
    #
    # ``insert`` consults each field's ``Field.db_default`` and skips
    # values that match the dataclass default -- so DB-side defaults
    # like ``nextval(...)`` and ``current_timestamp`` actually fire.
    # ------------------------------------------------------------------

    @classmethod
    def _qualified(cls) -> str:
        return f"{cls._resolve_schema(None)}.{cls._Meta.name}"

    @classmethod
    def _column_names(cls) -> list[str]:
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_row(cls, row: tuple[Any, ...]) -> Self:
        """Build an instance from a row tuple in dataclass field order.

        Passes values as kwargs rather than positional so classes with
        ``kw_only`` fields (e.g. :class:`~app.entities.places.Place`'s
        ``latitude`` / ``longitude``) still accept the row.
        """
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
    ) -> list[Self]:
        """Return every row matching the optional WHERE clause as instances."""
        from app.database import cursor

        cols = ", ".join(cls._column_names())
        sql = f"SELECT {cols} FROM {cls._qualified()}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with cursor(database=cls._resolve_database()) as cur:
            rows = cur.execute(sql, params or []).fetchall()
        return [cls.from_row(r) for r in rows]

    def insert(self) -> Self:
        """INSERT this row, letting DB defaults fire for fields whose value
        equals the dataclass default. Refreshes ``self`` from ``RETURNING``
        so DB-generated values (sequence ids, timestamps) are populated.
        """
        from app.database import cursor

        cls = type(self)

        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)
        insert_cols: list[str] = []
        insert_vals: list[Any] = []
        for f in dataclasses.fields(cls):
            current = getattr(self, f.name)
            meta = cls._get_field_obj(hints[f.name])
            has_db_default = meta is not None and meta.db_default is not None
            if f.default is not dataclasses.MISSING:
                default_val: Any = f.default
            elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
                default_val = f.default_factory()  # type: ignore[misc]
            else:
                default_val = None
            if has_db_default and current == default_val:
                continue
            insert_cols.append(f.name)
            insert_vals.append(current)
        col_list = ", ".join(insert_cols)
        placeholders = ", ".join(["?"] * len(insert_cols))
        return_cols = ", ".join(cls._column_names())
        sql = f"INSERT INTO {cls._qualified()} ({col_list}) VALUES ({placeholders}) RETURNING {return_cols}"
        with cursor(database=cls._resolve_database()) as cur:
            row = cur.execute(sql, insert_vals).fetchone()
        if row is None:
            msg = f"INSERT into {cls._qualified()} returned no row"
            raise RuntimeError(msg)
        for name, val in zip(cls._column_names(), row, strict=True):
            object.__setattr__(self, name, val)
        return self

    def save(self) -> Self:
        """UPDATE this row by primary key. Refreshes ``self`` from ``RETURNING``."""
        from app.database import cursor

        cls = type(self)

        set_cols = [c for c in cls._column_names() if c not in cls._Meta.pk]
        if not set_cols:
            return self
        set_clause = ", ".join(f"{c} = ?" for c in set_cols)
        where = " AND ".join(f"{c} = ?" for c in cls._Meta.pk)
        return_cols = ", ".join(cls._column_names())
        set_vals = [getattr(self, c) for c in set_cols]
        pk_vals = [getattr(self, c) for c in cls._Meta.pk]
        sql = f"UPDATE {cls._qualified()} SET {set_clause} WHERE {where} RETURNING {return_cols}"
        with cursor(database=cls._resolve_database()) as cur:
            row = cur.execute(sql, [*set_vals, *pk_vals]).fetchone()
        if row is None:
            msg = f"UPDATE in {cls._qualified()} found no row matching pk={pk_vals}"
            raise ValueError(msg)
        for name, val in zip(cls._column_names(), row, strict=True):
            object.__setattr__(self, name, val)
        return self

    def delete(self) -> None:
        """DELETE this row by primary key. Idempotent: no error if already gone."""
        from app.database import cursor

        cls = type(self)

        where = " AND ".join(f"{c} = ?" for c in cls._Meta.pk)
        pk_vals = [getattr(self, c) for c in cls._Meta.pk]
        with cursor(database=cls._resolve_database()) as cur:
            cur.execute(f"DELETE FROM {cls._qualified()} WHERE {where}", pk_vals)

    def upsert(self) -> Self:
        """Insert if no row with this PK exists, otherwise update.

        Two-statement (find then insert/save) -- backend-agnostic, no
        ON CONFLICT. For the small system tables this wraps, the extra
        round-trip is irrelevant.
        """
        cls = type(self)
        pk_vals = [getattr(self, c) for c in cls._Meta.pk]
        if cls.find(*pk_vals) is None:
            return self.insert()
        return self.save()

    @classmethod
    def clear_rows(cls, *, schema: str | None = None) -> None:
        """Delete every row from this table."""
        from app.database import cursor

        s = cls._resolve_schema(schema)

        with cursor(database=cls._resolve_database()) as cur:
            cur.execute(f"DELETE FROM {s}.{cls._Meta.name}")

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


class DataTable(Table):
    """Base for tables that hold user-observable data with a typed ``kind``.

    Splits the Table hierarchy into two families:

    - :class:`Table` -- system / registry / config tables (entity types,
      plugin install state, workspaces, hotkeys, singletons). Structural
      bookkeeping; no kind taxonomy.
    - :class:`DataTable` -- raw source data (via ``SourceTable`` and its
      kind subclasses) and derived metrics (via ``MetricTable`` and its
      grain subclasses). Every concrete subclass has a ``table_kind()``
      string from :data:`DataTable._KIND_BY_BASE_NAME`.
    """

    _abstract: ClassVar[bool] = True

    # Map of kind base class names to the kind string. Used by ``table_kind()``
    # to walk the MRO without importing the SourceTable / MetricTable subclasses
    # (which would create a circular dep). Inspecting class names instead of
    # identities keeps this in this module.
    #
    # Source-side kinds describe *load semantics* (how dlt writes the table);
    # metric-side kinds describe *query semantics* (how a downstream consumer
    # asks questions of an already-projected metric).
    _KIND_BY_BASE_NAME: ClassVar[dict[str, str]] = {
        # Source-side: load semantics
        "EventTable": "event",
        "IntervalTable": "interval",
        "AggregateTable": "aggregate",
        "DimensionTable": "dimension",
        "SnapshotTable": "snapshot",
        "CounterTable": "counter",
        "M2MTable": "m2m_relation",
        # Dataset-side: query semantics for derived metric tables
        "DailyMetricTable": "daily_metric",
        "WeeklyMetricTable": "weekly_metric",
        "MonthlyMetricTable": "monthly_metric",
        "EventMetricTable": "event_metric",
    }

    # One-line query hints, keyed by kind string. The LLM-facing catalog
    # surfaces these so a model can pick the right primitive without having
    # to know the SCD2 / observed_at / interval-overlap conventions itself.
    _QUERY_HINT_BY_KIND: ClassVar[dict[str, str]] = {
        # Source-side load-semantics hints
        "event": "Filter or window by `time_at` (or `observed_at` if no native timestamp). Merge on PK.",
        "interval": "Filter where `time_start <= ts AND time_end > ts` for overlap. Merge on PK.",
        "aggregate": "Point lookup on the window key (`time_at`). Merge on the PK that includes the window key.",
        "dimension": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro. Never naive equi-join.",
        "snapshot": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro to read the value at time ts.",
        "counter": "ORDER BY `observed_at` and use `lag()` to compute per-period deltas; raw values are cumulative.",
        "m2m_relation": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro to find which entities were linked at ts.",
        # Dataset-side query-semantics hints
        "daily_metric": "Per-day rollup. Filter or join on `date` (DATE). PK includes (date, source). Lag in days.",
        "weekly_metric": "Per-week rollup. Filter or join on `week` (DATE/VARCHAR). PK includes (week, source). Lag in weeks.",
        "monthly_metric": (
            "Per-month rollup. Filter or join on `month` (VARCHAR YYYY-MM). PK includes (month, source). Lag in months."
        ),
        "event_metric": (
            "Discrete event in the unified timeline. Filter or window by `occurred_at`. PK is typically (source, source_id)."
        ),
    }

    @classmethod
    def table_kind(cls) -> str | None:
        """Return the kind string ("event" / "interval" / ... / "event_metric").

        Walks the MRO to find the first kind base class from
        :data:`_KIND_BY_BASE_NAME`. Returns ``None`` for abstract intermediate
        bases that haven't picked a kind yet.
        """
        for base in cls.__mro__:
            kind = cls._KIND_BY_BASE_NAME.get(base.__name__)
            if kind is not None:
                return kind
        return None

    @classmethod
    def table_metadata(cls) -> dict[str, Any]:
        """Return structured metadata for this data table.

        Composes :meth:`Table.column_metadata` with identity keys plus
        DataTable-specific enrichment:

        - Identity: ``table``, ``display_name``, ``schema``,
          ``description``, ``primary_key``, ``columns``.
        - ``kind`` -- one of the seven source-side kind strings or four
          metric-grain strings; omitted when ``None``.
        - ``query_hint`` -- one-line natural-language hint from
          :data:`_QUERY_HINT_BY_KIND` for the LLM-facing catalog.
        - ``time_columns`` -- ``time_at`` / ``time_start`` / ``time_end`` /
          ``cursor_column`` / ``observed_at_injected`` keys (only those
          actually set on the class).
        - ``as_of_macro`` -- the qualified SCD2 macro name, set only on
          dimension / snapshot / m2m tables.

        Used by :meth:`shenas_datasets.core.dataset.Dataset.metadata`, the
        per-source ``Source.get_*_metadata`` helpers, and (eventually) the
        analytics catalog endpoint that feeds the LLM.
        """
        meta: dict[str, Any] = {
            "table": cls._Meta.name,
            "display_name": cls._Meta.display_name,
            "schema": cls._Meta.schema,
            "description": cls._Meta.description or cls.__doc__,
            "primary_key": list(cls._Meta.pk),
            "columns": cls.column_metadata(),
        }

        kind = cls.table_kind()
        if kind is not None:
            meta["kind"] = kind
            meta["query_hint"] = cls._QUERY_HINT_BY_KIND[kind]

        # Time-axis columns. Only emit keys whose ClassVars are actually set on
        # this class (most kind bases declare a subset). ``observed_at_injected``
        # comes from the ``_needs_observed_at`` classmethod that EventTable and
        # CounterTable override.
        time_cols: dict[str, Any] = {}
        for attr in ("time_at", "time_start", "time_end", "cursor_column"):
            val = getattr(cls, attr, None)
            if val:
                time_cols[attr] = val
        needs_observed_at = getattr(cls, "_needs_observed_at", None)
        if callable(needs_observed_at):
            try:
                injected = bool(needs_observed_at())
            except Exception:
                injected = False
            if injected:
                time_cols["observed_at_injected"] = True
        if time_cols:
            meta["time_columns"] = time_cols

        # AS-OF macro: only for SCD2 tables (dimension / snapshot / m2m_relation),
        # generated by apply_as_of_macros() on every Source.sync().
        if kind in ("dimension", "snapshot", "m2m_relation") and cls._Meta.schema:
            meta["as_of_macro"] = f"{cls._Meta.schema}.{cls._Meta.name}_as_of"

        return meta


class SingletonTable(Table):
    """Base for system tables that hold exactly one row.

    Replaces ad-hoc single-row read/write across the codebase. Concrete
    subclasses (``SourceConfig``, ``SourceAuth``, ``SystemSettings``,
    ``LocalSession``, ...) declare their dataclass fields and ``_Meta`` as
    usual; the singleton semantics live here:

    - :meth:`read_row` -- SELECT the single row as a dict, or ``None``.
    - :meth:`read_value` -- pluck one column from the row.
    - :meth:`write_row` -- merge with existing values, then DELETE + INSERT.

    The merge-on-write means callers can pass partial kwargs and only the
    named fields will be updated; everything else is preserved (or filled
    in from the dataclass defaults on first write).
    """

    _abstract: ClassVar[bool] = True

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        """Read the single row from this table as a dict, or None if empty."""
        from app.database import cursor

        s = cls._resolve_schema(schema)

        cols = [f.name for f in dataclasses.fields(cls)]
        col_list = ", ".join(cols)
        with cursor(database=cls._resolve_database()) as cur:
            row = cur.execute(f"SELECT {col_list} FROM {s}.{cls._Meta.name} LIMIT 1").fetchone()
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
        from app.database import cursor

        s = cls._resolve_schema(schema)

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
        with cursor(database=cls._resolve_database()) as cur:
            cur.execute(f"DELETE FROM {s}.{cls._Meta.name}")
            cur.execute(f"INSERT INTO {s}.{cls._Meta.name} ({col_names}) VALUES ({placeholders})", values)
