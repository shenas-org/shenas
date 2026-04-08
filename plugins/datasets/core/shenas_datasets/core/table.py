"""Dataset-side metric-table base class.

``MetricTable`` extends the common :class:`shenas_plugins.core.table.Table`
with the dataset-side concerns: a thin ``to_ddl()`` helper that delegates
to the existing :func:`shenas_plugins.core.ddl.generate_ddl`, and the
class-level shape that the future per-table transform machinery will hang
off (transform classmethod, upstream declaration, etc -- not in this PR).

Example
-------
::

    from typing import Annotated, ClassVar

    from shenas_plugins.core.field import Field
    from shenas_datasets.core.table import MetricTable

    class DailyHRV(MetricTable):
        table_name: ClassVar[str] = "daily_hrv"
        table_display_name: ClassVar[str] = "Daily HRV"
        table_description: ClassVar[str | None] = "One row per (date, source) HRV summary."
        table_pk: ClassVar[tuple[str, ...]] = ("date", "source")

        date: Annotated[str, Field(db_type="DATE", description="Calendar date")]
        source: Annotated[str, Field(db_type="VARCHAR", description="Data source")]
        rmssd: Annotated[float | None, Field(db_type="DOUBLE", description="...")] = None

The ``@dataclass`` decorator is auto-applied by the common ``Table``'s
``__init_subclass__``, so subclasses don't need to write it explicitly.
"""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.table import Table


class MetricTable(Table):
    """Base class for canonical metric tables (the ``metrics.*`` schema).

    A metric table is a downstream projection: nothing extracts it from an
    external API, and it has no SCD2 / cursor / write-disposition concerns.
    All it carries today is the schema (via the dataclass fields inherited
    from :class:`Table`) and a ``to_ddl()`` helper.

    The future per-MetricTable transform classmethod (Source -> Metric or
    Metric -> Metric) will live on this class -- intentionally not in this
    PR. The inheritance shape is set up so that adding it later is purely
    additive.
    """

    _abstract: ClassVar[bool] = True

    @classmethod
    def to_ddl(cls, *, schema: str = "metrics") -> str:
        """Render the ``CREATE TABLE IF NOT EXISTS <schema>.<name> (...)`` DDL.

        Thin wrapper around :func:`shenas_plugins.core.ddl.generate_ddl`.
        """
        from shenas_plugins.core.ddl import generate_ddl

        return generate_ddl(cls, schema=schema)
