"""Dataset-side table base class.

``DatasetTable`` extends :class:`app.table.DataTable` for canonical metric
tables in the ``datasets.*`` schema. Concrete tables set ``_Meta.time_at``
to declare their time axis (``"date"`` for daily, ``"week"`` for weekly,
``"month"`` for monthly, ``"occurred_at"`` etc. for discrete events).

The kind string is derived from ``_Meta.time_at`` at runtime:

- ``"date"``        -> kind ``"daily_metric"``
- ``"week"``        -> kind ``"weekly_metric"``
- ``"month"``       -> kind ``"monthly_metric"``
- anything else     -> kind ``"event_metric"``
"""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

from app.schema import DATASETS
from app.table import DataTable, Field

TransformId = Annotated[
    int,
    Field(
        db_type="INTEGER",
        description="Transform instance that produced this row",
        display_name="Transform ID",
    ),
]


class DatasetTable(DataTable):
    """Base class for canonical metric tables (the ``datasets.*`` schema).

    A dataset table is a downstream projection: nothing extracts it from an
    external API, and it has no SCD2 / cursor / write-disposition concerns.
    Every row carries ``transform_id`` identifying which Transform instance
    produced it, so multi-source transforms work and provenance is tracked.

    Concrete tables must set ``_Meta.time_at`` to declare the time column.
    """

    _abstract: ClassVar[bool] = True

    class _Meta:
        schema = DATASETS

    @classmethod
    def _time_extremum(cls, func: str) -> str | None:
        """Return MIN or MAX of this table's time column as an ISO date string (10 chars)."""
        time_col = getattr(cls._Meta, "time_at", None)
        if not time_col:
            return None
        try:
            from app.database import cursor

            schema = getattr(cls._Meta, "schema", None)
            schema_name = schema.name if hasattr(schema, "name") else str(schema or "datasets")
            qualified = f'"{schema_name}"."{cls._Meta.name}"'  # ty: ignore[unresolved-attribute]
            with cursor() as cur:
                row = cur.execute(f'SELECT {func}("{time_col}") FROM {qualified}').fetchone()
                if row and row[0]:
                    return str(row[0])[:10]
        except Exception:
            pass
        return None

    @classmethod
    def get_earliest_datetime(cls) -> str | None:
        """Return the earliest value of this table's time column as an ISO date string."""
        return cls._time_extremum("MIN")

    @classmethod
    def get_latest_datetime(cls) -> str | None:
        """Return the latest value of this table's time column as an ISO date string."""
        return cls._time_extremum("MAX")

    @classmethod
    def live_stats(cls) -> dict[str, Any]:
        """Query DuckDB for row count, earliest, and latest datetime of this table."""
        try:
            from app.database import cursor

            schema = getattr(cls._Meta, "schema", None)
            schema_name = schema.name if hasattr(schema, "name") else str(schema or "datasets")
            qualified = f'"{schema_name}"."{cls._Meta.name}"'  # ty: ignore[unresolved-attribute]
            with cursor() as cur:
                row = cur.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
                rows = row[0] if row else 0
            return {
                "rows": rows,
                "earliest": cls.get_earliest_datetime(),
                "latest": cls.get_latest_datetime(),
            }
        except Exception:
            return {"rows": 0, "earliest": None, "latest": None}
