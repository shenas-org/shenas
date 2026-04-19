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


@dataclass(frozen=True)
class PlotHint:
    """Structured hint for time-series visualization.

    Tells the frontend what to plot and how to render it.

    ``y``
        Column name for the y-axis (required).
    ``group_by``
        Column to split into separate series (e.g. ``"learning_language"``
        produces one line per language). ``None`` = single series.
    ``chart_type``
        ``"line"`` (default), ``"bar"``, ``"area"``, or ``"scatter"``.
    ``label``
        Human-readable label for this plot. Defaults to the ``y`` column's
        ``display_name`` from ``Field`` metadata.
    """

    y: str
    group_by: str | None = None
    chart_type: str = "line"
    label: str | None = None


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
        sequences: ClassVar[tuple[str, ...]] = ()
        plot: ClassVar[tuple[PlotHint, ...]] = ()
        # Entity projection: set on SourceTable subclasses to auto-project
        # rows into entities + statements at sync time.
        entity_type: ClassVar[str | None] = None
        entity_name_column: ClassVar[str | None] = None
        entity_projection: ClassVar[dict[str, str]] = {}
        entity_wikidata_qid: ClassVar[str | None] = None

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
    def _resolve_database(cls) -> str | None:
        if getattr(cls._Meta, "database", "user") == "system":
            return "shenas"
        return None

    @classmethod
    def _qualified(cls) -> str:
        return f"{cls._Meta.schema.name}.{cls._Meta.name}"  # ty: ignore[unresolved-attribute]

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


# ---------------------------------------------------------------------------
# DataRelation mixin: metadata for UI-exposed tables and views
# ---------------------------------------------------------------------------


class DataRelation:
    """Mixin for tables/views exposed in the UI (sources, datasets).

    Provides ``metadata()`` and ``kind()`` for structured introspection.
    Internal system tables (hotkeys, workspace, plugin instances) don't
    need these and inherit only from Table/View directly.
    """

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

    @classmethod
    def kind(cls) -> str | None:
        """Return the kind string from the MRO."""
        for base in cls.__mro__:
            result = cls._KIND_BY_BASE_NAME.get(base.__name__)
            if result is not None:
                return result
        return None

    @classmethod
    def _time_column_metadata(cls) -> dict[str, Any]:
        """Extract time column info from _Meta and class attributes."""
        meta_obj = getattr(cls, "_Meta", None)
        time_cols: dict[str, Any] = {}
        for attr in ("time_at", "time_start", "time_end"):
            val = getattr(meta_obj, attr, None)
            if val:
                time_cols[attr] = val
        cursor_val = getattr(cls, "cursor_column", None)
        if cursor_val:
            time_cols["cursor_column"] = cursor_val
        needs_observed_at = getattr(cls, "_needs_observed_at", None)
        if callable(needs_observed_at):
            try:
                if needs_observed_at():
                    time_cols["observed_at_injected"] = True
            except Exception:
                pass
        return time_cols

    @classmethod
    def metadata(cls) -> dict[str, Any]:
        """Return structured metadata for this data table/view."""
        meta_obj = getattr(cls, "_Meta", None)
        meta: dict[str, Any] = {
            "table": getattr(meta_obj, "name", ""),
            "display_name": getattr(meta_obj, "display_name", ""),
            "schema": getattr(meta_obj, "schema", None),
            "description": getattr(meta_obj, "description", None) or cls.__doc__,
            "primary_key": list(getattr(meta_obj, "pk", ())),
            "columns": cls.column_metadata(),  # ty: ignore[unresolved-attribute]
        }

        table_kind = cls.kind()
        if table_kind is not None:
            meta["kind"] = table_kind
            hint = cls._QUERY_HINT_BY_KIND.get(table_kind)
            if hint:
                meta["query_hint"] = hint

        time_cols = cls._time_column_metadata()
        if time_cols:
            meta["time_columns"] = time_cols

        schema = getattr(meta_obj, "schema", None)
        if table_kind in ("dimension", "snapshot", "m2m_relation") and schema:
            meta["as_of_macro"] = f"{schema}.{getattr(meta_obj, 'name', '')}_as_of"

        plot = getattr(meta_obj, "plot", ())
        if plot:
            meta["plot"] = [dataclasses.asdict(p) for p in plot]

        entity_type = getattr(meta_obj, "entity_type", None)
        if entity_type:
            meta["entity_type"] = entity_type
        entity_projection = getattr(meta_obj, "entity_projection", None)
        if entity_projection:
            meta["entity_projection"] = dict(entity_projection)

        return meta

        return meta
