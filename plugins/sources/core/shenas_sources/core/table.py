"""Abstract source-table base classes.

Each raw source table is a class inheriting from one of the six kind-specific
base classes (``EventTable``, ``IntervalTable``, ``SnapshotTable``,
``DimensionTable``, ``AggregateTable``, ``CounterTable``). The kind is encoded
in the inheritance chain rather than as a magic string -- the type system
enforces the per-kind required class attributes at definition time, and each
kind base owns its own ``write_disposition()`` so the dlt loader gets the
right strategy automatically:

- ``EventTable``     -> ``"merge"`` on PK; observed_at auto-injected if no time_at
- ``IntervalTable``  -> ``"merge"`` on PK; requires time_start + time_end
- ``AggregateTable`` -> ``"merge"`` on PK; requires time_at = window key
- ``DimensionTable`` -> ``{"disposition": "merge", "strategy": "scd2"}``
- ``SnapshotTable``  -> ``{"disposition": "merge", "strategy": "scd2"}``
- ``CounterTable``   -> ``"append"`` with observed_at; requires counter_columns

Concrete subclasses just declare their schema fields, set ``name``,
``display_name``, ``pk``, and any kind-specific metadata, and implement
:meth:`Table.extract`. The class itself becomes a dlt resource via
:meth:`Table.to_resource`.

Example
-------
::

    class Categories(DimensionTable):
        name = "categories"
        display_name = "Lunch Money Categories"
        description = "Spending categories the user has defined."
        pk = ("id",)

        id: Annotated[int, Field(db_type="INTEGER", description="Category ID")]
        name_: Annotated[str, Field(db_type="VARCHAR", description="Category name")]

        @classmethod
        def extract(cls, client, **_):
            for c in client.get_categories():
                yield c.model_dump(mode="json")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from shenas_plugins.core.field import TableKind  # noqa: TC001  -- needed at runtime by get_type_hints walking the MRO

if TYPE_CHECKING:
    from collections.abc import Iterator


class Table:
    """Abstract base class for raw source tables.

    **Don't inherit from this directly** -- use one of the six kind-specific
    bases below (``EventTable``, ``IntervalTable``, etc.). The kind is encoded
    in the inheritance chain.

    Required class attributes on every concrete subclass
    ----------------------------------------------------
    name           : dlt resource name + DuckDB table name
    display_name   : human-readable label for the frontend
    pk             : tuple of natural primary key column names

    Optional
    --------
    description    : free-text description (rendered in dashboards)
    """

    # Concrete subclasses must override these.
    name: ClassVar[str]
    display_name: ClassVar[str]
    pk: ClassVar[tuple[str, ...]]
    kind: ClassVar[TableKind]  # set by each kind base class

    description: ClassVar[str | None] = None

    # Optional incremental-cursor column (only meaningful for non-SCD2 kinds).
    # When set, ``to_resource`` wires a ``dlt.sources.incremental(cursor_column)``
    # parameter into the generated resource and passes the cursor object to
    # ``extract`` as a ``cursor`` kwarg.
    cursor_column: ClassVar[str | None] = None

    # Internal: True on Table itself and on each kind base; False on concrete
    # subclasses (auto-set by __init_subclass__). Skips validation + the
    # @dataclass decorator for abstract base classes.
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

        Each kind base class extends this to enforce its own requirements.
        """
        for required in ("name", "display_name", "pk", "kind"):
            if not getattr(cls, required, None):
                msg = f"{cls.__name__}: missing required class attribute `{required}`"
                raise TypeError(msg)

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
        """Build the dlt column schema from this Table's dataclass fields.

        Currently delegates to ``shenas_datasets.core.dlt.dataclass_to_dlt_columns``
        for compatibility with the legacy resources.py callsites in source plugins
        that haven't yet migrated to the Table ABC. Once all sources migrate,
        the helper has zero callers and a final cleanup PR can fold its body
        inline here and delete it from ``datasets/core/dlt.py``.
        """
        from shenas_datasets.core.dlt import dataclass_to_dlt_columns

        columns = dataclass_to_dlt_columns(cls)
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
            "name": cls.name,
            "primary_key": list(cls.pk),
            "write_disposition": cls.write_disposition(),
            "columns": cls.to_dlt_columns(),
        }

        def _maybe_inject(row: dict[str, Any], now: str | None) -> dict[str, Any]:
            if needs_observed_at and "observed_at" not in row:
                return {**row, "observed_at": now}
            return row

        if cursor_column:

            @dlt.resource(**common)
            def _gen(
                cursor: Any = dlt.sources.incremental(cursor_column, initial_value=None),
            ) -> Iterator[dict[str, Any]]:
                now = datetime.now(UTC).isoformat() if needs_observed_at else None
                for row in cls.extract(client, cursor=cursor, **context):
                    yield _maybe_inject(row, now)

        else:

            @dlt.resource(**common)
            def _gen() -> Iterator[dict[str, Any]]:
                now = datetime.now(UTC).isoformat() if needs_observed_at else None
                for row in cls.extract(client, **context):
                    yield _maybe_inject(row, now)

        return _gen()


# ---------------------------------------------------------------------------
# Kind-specific base classes -- inherit from one of these
# ---------------------------------------------------------------------------


class EventTable(Table):
    """A discrete, immutable point-in-time event. Merge on PK.

    Optional ``time_at`` declares which column holds the row's timestamp;
    if omitted, an ``observed_at`` column is auto-injected from sync time.
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "event"
    time_at: ClassVar[str | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "merge"

    @classmethod
    def _needs_observed_at(cls) -> bool:
        return cls.time_at is None


class IntervalTable(Table):
    """A discrete occurrence with both a start and an end timestamp. Merge on PK.

    Both ``time_start`` and ``time_end`` are required.
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "interval"
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


class AggregateTable(Table):
    """Per-window summary keyed on a time-window column. Merge on PK (which includes the window key).

    ``time_at`` should match the window-key column in ``pk`` (date / hour / etc).
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "aggregate"
    time_at: ClassVar[str | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return "merge"


class DimensionTable(Table):
    """Reference / lookup data that other tables join against. Loaded as SCD2.

    Optional ``scd_columns`` lists the value columns whose changes mint a new
    version. Defaults to all non-pk fields.
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "dimension"
    scd_columns: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return {"disposition": "merge", "strategy": "scd2"}


class SnapshotTable(Table):
    """Current self-state with no temporal axis. Loaded as SCD2 (hash-then-version).

    Same write semantics as ``DimensionTable`` but flagged separately so
    dashboards know it's leaf state, not a joinable lookup.
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "snapshot"
    scd_columns: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def write_disposition(cls) -> dict[str, str] | str:
        return {"disposition": "merge", "strategy": "scd2"}


class CounterTable(Table):
    """Monotonically growing scalar where deltas matter. Append-with-observed_at.

    ``counter_columns`` is required and lists the cumulative columns.
    """

    _abstract: ClassVar[bool] = True
    kind: ClassVar[TableKind] = "counter"
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
