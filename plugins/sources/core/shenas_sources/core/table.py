"""Source-side raw-table base class.

``SourceTable`` extends the common :class:`shenas_plugins.core.table.Table`
with everything that's specific to *raw, freshly synced source data*: a
``kind`` taxonomy, dlt resource translation (write_disposition + columns),
optional incremental cursors, and auto-injection of ``observed_at`` for
tables without a native timestamp.

Each raw source table is a class inheriting from one of the seven
kind-specific base classes (``EventTable``, ``IntervalTable``,
``SnapshotTable``, ``DimensionTable``, ``AggregateTable``, ``CounterTable``,
``M2MTable``). The kind is encoded in the inheritance chain rather than as
a magic string -- the type system enforces the per-kind required class
attributes at definition time, and each kind base owns its own
``write_disposition()`` so the dlt loader gets the right strategy
automatically:

- ``EventTable``     -> ``"merge"`` on PK; observed_at auto-injected if no time_at
- ``IntervalTable``  -> ``"merge"`` on PK; requires time_start + time_end
- ``AggregateTable`` -> ``"merge"`` on PK; requires time_at = window key
- ``DimensionTable`` -> ``{"disposition": "merge", "strategy": "scd2"}``
- ``SnapshotTable``  -> ``{"disposition": "merge", "strategy": "scd2"}``
- ``CounterTable``   -> ``"append"`` with observed_at; requires counter_columns
- ``M2MTable``       -> ``{"disposition": "merge", "strategy": "scd2"}``; PK >= 2 cols

Concrete subclasses just declare their schema fields, set ``name``,
``display_name``, ``pk``, and any kind-specific metadata, and implement
:meth:`SourceTable.extract`. The class itself becomes a dlt resource via
:meth:`SourceTable.to_resource`.

Example
-------
::

    class Categories(DimensionTable):
        table_name = "categories"
        table_display_name = "Lunch Money Categories"
        table_description = "Spending categories the user has defined."
        table_pk = ("id",)

        id: Annotated[int, Field(db_type="INTEGER", description="Category ID")]
        name_: Annotated[str, Field(db_type="VARCHAR", description="Category name")]

        @classmethod
        def extract(cls, client, **_):
            for c in client.get_categories():
                yield c.model_dump(mode="json")
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from app.table import DataTable

if TYPE_CHECKING:
    from collections.abc import Iterator


# Map DuckDB types (as produced by shenas_plugins.core.ddl._duckdb_type) to
# dlt's type system. Used by SourceTable.to_dlt_columns().
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


class SourceTable(DataTable):
    """Abstract base class for raw source tables.

    **Don't inherit from this directly** -- use one of the seven kind-specific
    bases below (``EventTable``, ``IntervalTable``, etc.). The kind is encoded
    in the inheritance chain.
    """

    _abstract: ClassVar[bool] = True

    # Optional incremental-cursor column (only meaningful for non-SCD2 kinds).
    # When set, ``to_resource`` wires a ``dlt.sources.incremental(cursor_column)``
    # parameter into the generated resource and passes the cursor object to
    # ``extract`` as a ``cursor`` kwarg.
    cursor_column: ClassVar[str | None] = None

    # ------------------------------------------------------------------
    # dlt translation -- kind base classes override write_disposition()
    # ------------------------------------------------------------------

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        """Return the dlt write_disposition for this table's kind.

        Default is ``"merge"``. Kind base classes override.
        """
        return "merge"

    @classmethod
    def to_dlt_columns(cls) -> dict[str, dict[str, Any]]:
        """Build the dlt column schema from this Table's dataclass fields."""
        import dataclasses
        from typing import get_type_hints

        hints = get_type_hints(cls, include_extras=True)
        columns: dict[str, dict[str, Any]] = {}
        for f in dataclasses.fields(cls):
            if f.name.startswith("_"):
                continue
            hint = hints[f.name]
            db_type = cls._duckdb_type(hint).lower()
            dlt_type = _DLT_TYPE_MAP.get(db_type, "text")
            col: dict[str, Any] = {"name": f.name, "data_type": dlt_type}

            meta = cls._get_field_obj(hint)
            if meta and meta.description:
                col["description"] = meta.description

            columns[f.name] = col

        if cls._needs_observed_at():
            columns["observed_at"] = {
                "name": "observed_at",
                "data_type": "timestamp",
                "description": "Auto-injected sync timestamp (no native time column on this table).",
            }
        return columns

    @classmethod
    def _needs_observed_at(cls) -> bool:
        """An event/counter table without a native timestamp gets observed_at injected.

        Overridden by kind base classes that always inject (counter) or never (interval).
        """
        return False

    @classmethod
    def extract(cls, client: Any, **context: Any) -> Iterator[dict[str, Any]]:
        """Yield rows. Subclasses implement.

        ``context`` is a free-form dict of shared state across multiple tables in
        one sync (e.g. strava pre-fetches a list of detailed activities and
        passes it to several Tables that all derive from it).
        """
        msg = f"{cls.__name__}.extract not implemented"
        raise NotImplementedError(msg)

    @classmethod
    def to_resource(cls, client: Any, **context: Any) -> Any:
        """Build a dlt resource bound to this Table's metadata + extract method.

        If ``cursor_column`` is set, a ``dlt.sources.incremental`` parameter is
        wired into the generated resource and the resulting cursor object is
        passed to :meth:`extract` as a ``cursor`` keyword argument.
        """
        import dlt

        needs_observed_at = cls._needs_observed_at()
        cursor_column = cls.cursor_column

        common = {
            "name": cls._Meta.name,
            "primary_key": list(cls._Meta.pk),
            "write_disposition": cls.write_disposition(),
            "columns": cls.to_dlt_columns(),
        }

        def _maybe_inject(row: dict[str, Any], now: str | None) -> dict[str, Any]:
            if needs_observed_at and "observed_at" not in row:
                return {**row, "observed_at": now}
            return row

        if cursor_column:

            @dlt.resource(**common)  # ty: ignore[invalid-argument-type]
            def _gen(
                cursor: Any = dlt.sources.incremental(cursor_column, initial_value=None),
            ) -> Iterator[dict[str, Any]]:
                now = datetime.now(UTC).isoformat() if needs_observed_at else None
                for row in cls.extract(client, cursor=cursor, **context):
                    yield _maybe_inject(row, now)

        else:

            @dlt.resource(**common)  # ty: ignore[invalid-argument-type]
            def _gen() -> Iterator[dict[str, Any]]:
                now = datetime.now(UTC).isoformat() if needs_observed_at else None
                for row in cls.extract(client, **context):
                    yield _maybe_inject(row, now)

        return _gen()


# ---------------------------------------------------------------------------
# Kind-specific base classes -- inherit from one of these
# ---------------------------------------------------------------------------


class EventTable(SourceTable):
    """A discrete, immutable point-in-time event. Merge on PK.

    Optional ``time_at`` declares which column holds the row's timestamp;
    if omitted, an ``observed_at`` column is auto-injected from sync time.
    """

    _abstract: ClassVar[bool] = True
    time_at: ClassVar[str | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "merge"

    @classmethod
    def _needs_observed_at(cls) -> bool:
        return cls.time_at is None


class IntervalTable(SourceTable):
    """A discrete occurrence with both a start and an end timestamp. Merge on PK.

    Both ``time_start`` and ``time_end`` are required.
    """

    _abstract: ClassVar[bool] = True
    time_start: ClassVar[str]
    time_end: ClassVar[str]

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "merge"

    @classmethod
    def _validate(cls) -> None:
        super()._validate()
        if not getattr(cls, "time_start", None) or not getattr(cls, "time_end", None):
            msg = f"{cls.__name__}: IntervalTable requires both `time_start` and `time_end`"
            raise TypeError(msg)


class AggregateTable(SourceTable):
    """Per-window summary keyed on a time-window column. Merge on PK (which includes the window key).

    ``time_at`` should match the window-key column in ``pk`` (date / hour / etc).
    """

    _abstract: ClassVar[bool] = True
    time_at: ClassVar[str | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "merge"


class DimensionTable(SourceTable):
    """Reference / lookup data that other tables join against. Loaded as SCD2.

    Optional ``scd_columns`` lists the value columns whose changes mint a new
    version. Defaults to all non-pk fields.
    """

    _abstract: ClassVar[bool] = True
    scd_columns: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return {"disposition": "merge", "strategy": "scd2"}


class SnapshotTable(SourceTable):
    """Current self-state with no temporal axis. Loaded as SCD2 (hash-then-version).

    Same write semantics as ``DimensionTable`` but flagged separately so
    dashboards know it's leaf state, not a joinable lookup.
    """

    _abstract: ClassVar[bool] = True
    scd_columns: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return {"disposition": "merge", "strategy": "scd2"}


class CounterTable(SourceTable):
    """Monotonically growing scalar where deltas matter. Append-with-observed_at.

    ``counter_columns`` is required and lists the cumulative columns.
    """

    _abstract: ClassVar[bool] = True
    counter_columns: ClassVar[tuple[str, ...]]

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "append"

    @classmethod
    def _needs_observed_at(cls) -> bool:
        return True

    @classmethod
    def _validate(cls) -> None:
        super()._validate()
        if not getattr(cls, "counter_columns", None):
            msg = f"{cls.__name__}: CounterTable requires `counter_columns`"
            raise TypeError(msg)


class M2MTable(SourceTable):
    """Many-to-many bridge table joining two entities. Loaded as SCD2.

    PK is the composite of the two foreign keys (must be at least 2 columns).
    Rows typically have NO additional value columns -- denormalized attributes
    belong on the entity dimensions and are joined when needed. Removals are
    detected by SCD2 and close the row's ``_dlt_valid_to``, so historical
    "what entities were linked at time T" queries return what was true then,
    not what's true now.

    This is structurally identical to ``DimensionTable`` (same SCD2 loader)
    but flagged separately because it represents a graph edge, not standalone
    reference data. Dashboards can render m2m tables as bipartite filters or
    graph edges; dimensions as filter dropdowns.
    """

    _abstract: ClassVar[bool] = True

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return {"disposition": "merge", "strategy": "scd2"}

    @classmethod
    def _validate(cls) -> None:
        super()._validate()
        if len(cls._Meta.pk) < 2:
            msg = (
                f"{cls.__name__}: M2MTable requires a composite PK with at least 2 "
                f"columns (the two foreign keys); got {cls._Meta.pk!r}"
            )
            raise TypeError(msg)


# EntityTable has moved to app.entity to live alongside its companion types
# (EntityType, Entity, EntityIndex). Import it from there:
#
#     from app.entity import EntityTable
