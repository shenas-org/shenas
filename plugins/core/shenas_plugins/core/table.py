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

from dataclasses import dataclass
from typing import Any, ClassVar


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
