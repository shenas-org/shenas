"""Dataset-side metric-table base class.

``MetricTable`` extends the common :class:`shenas_plugins.core.table.Table`
with the dataset-side concerns -- currently nothing more than a marker
class. The future per-table transform classmethods (Source -> Metric and
Metric -> Metric) will live here. The DDL helpers (``to_ddl()``,
``ensure()``, ``table_metadata()``) are inherited from ``Table``.
"""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.table import Table


class MetricTable(Table):
    """Base class for canonical metric tables (the ``metrics.*`` schema).

    A metric table is a downstream projection: nothing extracts it from an
    external API, and it has no SCD2 / cursor / write-disposition concerns.
    All it carries today is the schema (via the dataclass fields inherited
    from :class:`Table`) and the inherited DDL / metadata helpers.

    The future per-MetricTable transform classmethod (Source -> Metric or
    Metric -> Metric) will live on this class -- intentionally not in this
    PR. The inheritance shape is set up so that adding it later is purely
    additive.
    """

    _abstract: ClassVar[bool] = True
    table_schema: ClassVar[str | None] = "metrics"
