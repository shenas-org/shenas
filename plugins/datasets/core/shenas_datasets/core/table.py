"""Dataset-side metric-table base class + grain-specific subclasses.

``MetricTable`` extends the common :class:`shenas_plugins.core.table.Table`
for canonical metric tables in the ``metrics.*`` schema. Concrete metric
tables should inherit from one of the **grain-specific subclasses** below
rather than from ``MetricTable`` directly, so the catalog can advertise
their natural query axis to LLM consumers:

- :class:`DailyMetricTable`   -- one row per (date, source); ``time_at = "date"``
- :class:`WeeklyMetricTable`  -- one row per (week, source); ``time_at = "week"``
- :class:`MonthlyMetricTable` -- one row per (month, source); ``time_at = "month"``
- :class:`EventMetricTable`   -- discrete events keyed on (source, source_id);
  ``time_at = "occurred_at"``

These exist purely so the catalog knows the time semantics of derived
metric tables. They mirror the seven *source-side* kind base classes
(``EventTable``, ``IntervalTable``, ...) which encode load semantics for
raw sync data; the metric kinds encode the equivalent *query semantics*
for downstream projections.
"""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.table import Table


class MetricTable(Table):
    """Base class for canonical metric tables (the ``metrics.*`` schema).

    A metric table is a downstream projection: nothing extracts it from an
    external API, and it has no SCD2 / cursor / write-disposition concerns.
    Concrete metric tables should inherit from one of the grain-specific
    subclasses below (``DailyMetricTable`` etc.) so the catalog advertises
    their time semantics. ``MetricTable`` itself stays as the abstract root
    so future per-table transform classmethods (Source -> Metric, Metric ->
    Metric) have a single home.
    """

    _abstract: ClassVar[bool] = True
    table_schema: ClassVar[str | None] = "metrics"


class DailyMetricTable(MetricTable):
    """Per-day metric. PK should include ``date``; ``time_at = "date"``."""

    _abstract: ClassVar[bool] = True
    time_at: ClassVar[str] = "date"


class WeeklyMetricTable(MetricTable):
    """Per-week metric. PK should include ``week``; ``time_at = "week"``."""

    _abstract: ClassVar[bool] = True
    time_at: ClassVar[str] = "week"


class MonthlyMetricTable(MetricTable):
    """Per-month metric. PK should include ``month``; ``time_at = "month"``."""

    _abstract: ClassVar[bool] = True
    time_at: ClassVar[str] = "month"


class EventMetricTable(MetricTable):
    """Discrete event metric. PK is typically (source, source_id).

    Distinct from a ``DailyMetricTable``: events have point-in-time
    timestamps, not window keys. Use this for the unified event timeline
    (``metrics.events``), individual financial transactions, etc.

    Subclasses must set ``time_at`` explicitly because the column naming
    convention varies (``occurred_at``, ``start_at``, ``date``, ...).
    """

    _abstract: ClassVar[bool] = True
