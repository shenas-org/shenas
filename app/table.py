"""Table: physical DuckDB table with DDL + write operations.

Inherits all read-only machinery from :class:`~app.relation.Relation`
and adds ``to_ddl``, ``ensure``, ``insert``, ``save``, ``delete``,
``upsert``, and ``clear_rows``.

Re-exports :class:`~app.relation.Field` and :class:`~app.relation.Relation`
so existing ``from app.table import Field, Table`` imports keep working.
"""

from __future__ import annotations

import contextlib
import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, Self, get_type_hints

import duckdb

# Re-export so callers can keep doing ``from app.table import Field, Table``.
from app.relation import Field, Relation  # noqa: F401
from app.view import View  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Sequence


class Table(Relation):
    """A physical DuckDB table with DDL generation and write operations.

    Required ``_Meta`` attributes (in addition to Relation's):
    ``pk`` -- tuple of natural primary key column names.
    """

    _abstract: ClassVar[bool] = True

    @classmethod
    def _validate(cls) -> None:
        super()._validate()
        if not getattr(cls._Meta, "pk", None):
            msg = f"{cls.__name__}: _Meta missing required attribute `pk`"
            raise TypeError(msg)

    @classmethod
    def to_ddl(cls, *, schema: str = "metrics") -> str:
        """Render the ``CREATE TABLE IF NOT EXISTS`` DDL."""
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
    def ensure(cls, *, schema: str | None = None) -> None:
        """Create this table if missing, then add any new columns.

        Uses the cursor system from :mod:`app.database`.
        """
        from app.database import cursor

        s = schema or getattr(cls._Meta, "schema", None) or "metrics"
        with cursor(database=cls._resolve_database()) as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}"')
            cur.execute(cls.to_ddl(schema=s))
            cls._add_missing_columns(cur, schema=s)

    @classmethod
    def _add_missing_columns(cls, cur: duckdb.DuckDBPyConnection, *, schema: str = "metrics") -> None:
        """Add columns that exist on the dataclass but not in the live DuckDB table."""
        hints: dict[str, type] = get_type_hints(cls, include_extras=True)
        existing = {
            row[0]
            for row in cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
                [schema, cls._Meta.name],
            ).fetchall()
        }
        for f in dataclasses.fields(cls):
            if f.name not in existing:
                col_type = cls._duckdb_type(hints[f.name])
                with contextlib.suppress(duckdb.CatalogException):
                    cur.execute(f'ALTER TABLE "{schema}"."{cls._Meta.name}" ADD COLUMN "{f.name}" {col_type}')

    # ------------------------------------------------------------------
    # Write CRUD (insert / save / delete / upsert / clear_rows)
    # ------------------------------------------------------------------

    def insert(self) -> Self:
        """INSERT this row, letting DB defaults fire for defaulted fields."""
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
        """UPDATE this row by primary key."""
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
        """DELETE this row by primary key. Idempotent."""
        from app.database import cursor

        cls = type(self)

        where = " AND ".join(f"{c} = ?" for c in cls._Meta.pk)
        pk_vals = [getattr(self, c) for c in cls._Meta.pk]
        with cursor(database=cls._resolve_database()) as cur:
            cur.execute(f"DELETE FROM {cls._qualified()} WHERE {where}", pk_vals)

    def upsert(self) -> Self:
        """Insert if no row with this PK exists, otherwise update."""
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

    @staticmethod
    def ensure_schema(all_tables: Sequence[type[Table]], *, schema: str = "metrics") -> None:
        """Create the named schema and ensure every table exists."""
        from app.database import cursor

        with cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for t in all_tables:
            t.ensure(schema=schema)


# ---------------------------------------------------------------------------
# DataTable: kind-aware base for source + dataset tables
# ---------------------------------------------------------------------------


class DataTable(Table):
    """Base for tables with a typed ``kind`` (source data or metrics)."""

    _abstract: ClassVar[bool] = True

    _KIND_BY_BASE_NAME: ClassVar[dict[str, str]] = {
        "EventTable": "event",
        "IntervalTable": "interval",
        "AggregateTable": "aggregate",
        "DimensionTable": "dimension",
        "SnapshotTable": "snapshot",
        "CounterTable": "counter",
        "M2MTable": "m2m_relation",
        "DailyMetricTable": "daily_metric",
        "WeeklyMetricTable": "weekly_metric",
        "MonthlyMetricTable": "monthly_metric",
        "EventMetricTable": "event_metric",
    }

    _QUERY_HINT_BY_KIND: ClassVar[dict[str, str]] = {
        "event": "Filter or window by `time_at` (or `observed_at` if no native timestamp). Merge on PK.",
        "interval": "Filter where `time_start <= ts AND time_end > ts` for overlap. Merge on PK.",
        "aggregate": "Point lookup on the window key (`time_at`). Merge on the PK that includes the window key.",
        "dimension": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro. Never naive equi-join.",
        "snapshot": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro to read the value at time ts.",
        "counter": "ORDER BY `observed_at` and use `lag()` to compute per-period deltas; raw values are cumulative.",
        "m2m_relation": "AS-OF lookup via the `<schema>.<table>_as_of(ts)` macro to find which entities were linked at ts.",
        "daily_metric": "Per-day rollup. Filter or join on `date` (DATE). PK includes (date, source). Lag in days.",
        "weekly_metric": "Per-week rollup. Filter or join on `week` (DATE/VARCHAR). PK includes (week, source). Lag in weeks.",
        "monthly_metric": (
            "Per-month rollup. Filter or join on `month` (VARCHAR YYYY-MM). PK includes (month, source). Lag in months."
        ),
        "event_metric": (
            "Discrete event in the unified timeline. Filter or window by `occurred_at`. PK is typically (source, source_id)."
        ),
    }

    _SCD2_KINDS: ClassVar[frozenset[str]] = frozenset({"dimension", "snapshot", "m2m_relation"})

    @classmethod
    def is_scd2(cls) -> bool:
        """True if this table uses SCD2 versioning."""
        return cls.table_kind() in cls._SCD2_KINDS

    @classmethod
    def scd2_filter(cls, as_of: str | None = None, *, alias: str = "") -> str:
        """Return a SQL WHERE fragment for reading SCD2 tables."""
        if not cls.is_scd2():
            return ""
        pfx = f"{alias}." if alias else ""
        if as_of is None:
            return f"{pfx}_dlt_valid_to IS NULL"
        return f"{pfx}_dlt_valid_from <= '{as_of}' AND ({pfx}_dlt_valid_to IS NULL OR {pfx}_dlt_valid_to > '{as_of}')"

    @classmethod
    def table_kind(cls) -> str | None:
        """Return the kind string from the MRO."""
        for base in cls.__mro__:
            kind = cls._KIND_BY_BASE_NAME.get(base.__name__)
            if kind is not None:
                return kind
        return None

    @classmethod
    def table_metadata(cls) -> dict[str, Any]:
        """Return structured metadata for this data table."""
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

        time_cols: dict[str, Any] = {}
        for attr in ("time_at", "time_start", "time_end"):
            val = getattr(cls._Meta, attr, None)
            if val:
                time_cols[attr] = val
        cursor_val = getattr(cls, "cursor_column", None)
        if cursor_val:
            time_cols["cursor_column"] = cursor_val
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

        if kind in ("dimension", "snapshot", "m2m_relation") and cls._Meta.schema:
            meta["as_of_macro"] = f"{cls._Meta.schema}.{cls._Meta.name}_as_of"

        return meta


# ---------------------------------------------------------------------------
# SingletonTable: single-row CRUD wrapper
# ---------------------------------------------------------------------------


class SingletonTable(Table):
    """Base for system tables that hold exactly one row."""

    _abstract: ClassVar[bool] = True

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        """Read the single row as a dict, or None if empty."""
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
        """Upsert the single row: merge with existing, then DELETE + INSERT."""
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


# ---------------------------------------------------------------------------
# KeyValueTable: two-column (key, value) pattern
# ---------------------------------------------------------------------------


class KeyValueTable(Table):
    """Base for simple two-column (key, value) tables.

    Marks tables that use the K-V pattern so they're easy to find if we
    ever introduce a proper key-value store. Concrete subclasses declare
    ``_Meta`` (name, display_name, schema) plus the two columns::

        class MyKV(KeyValueTable):
            class _Meta:
                name = "my_kv"
                display_name = "My KV"
                schema = "cache"

            key: Annotated[str, Field(db_type="TEXT", description="...")] = ""
            value: Annotated[str, Field(db_type="TEXT", description="...")] = ""

    Convenience helpers:

    - ``get(key)`` -- return the value string, or ``None``.
    - ``put(key, value)`` -- upsert the row.
    """

    _abstract: ClassVar[bool] = True

    class _Meta:
        pk: ClassVar[tuple[str, ...]] = ("key",)

    @classmethod
    def get(cls, key: str) -> str | None:
        """Return the value for ``key``, or ``None``."""
        row = cls.find(key)
        return row.value if row else None  # ty: ignore[unresolved-attribute]

    @classmethod
    def put(cls, key: str, value: str) -> None:
        """Upsert ``(key, value)``."""
        cls.from_row((key, value)).upsert()
