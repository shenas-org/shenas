"""Unified timeseries views across all dataset tables.

Builds a set of ``CREATE OR REPLACE VIEW`` statements that join every
dataset table into a single wide timeseries bucketed at 15-minute
intervals, plus downsampled companions at hourly, daily, weekly,
monthly, and yearly grains.

The column set is discovered dynamically from ``DatasetTable``
subclasses so new datasets appear automatically on the next refresh.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import get_type_hints

from app.relation import Field
from app.schema import DATASETS
from app.view import DataView

log = logging.getLogger("shenas.timeseries")

# Map DuckDB types to default aggregation functions (same as source.py).
_AGG_MAP: dict[str, str] = {
    "integer": "SUM",
    "bigint": "SUM",
    "double": "AVG",
    "float": "AVG",
    "real": "AVG",
    "boolean": "BOOL_OR",
}

# Columns that are never included in the timeseries view.
_SKIP_COLS = frozenset({"source", "transform_id", "id", "source_device"})

# Grains that select from the 15-min base view.
# Key is the view suffix; value is the date_trunc specifier.
_BASE_CHILDREN = {
    "hourly": "hour",
    "daily": "day",
}
# Grains that select from the daily view for efficiency.
_DAILY_CHILDREN = {
    "weekly": "week",
    "monthly": "month",
    "yearly": "year",
}

# Registry of view classes for catalog discovery.
TIMESERIES_VIEWS: list[type[DataView]] = []


# ---------------------------------------------------------------------------
# Column discovery
# ---------------------------------------------------------------------------


def _discover_agg_columns(table_cls: type) -> list[tuple[str, str, str]]:
    """Extract (agg_fn, column_name, alias) tuples from a DatasetTable class.

    Skips non-aggregatable columns (text, JSON), system columns, PK columns,
    and the time column itself.
    """
    meta = table_cls._Meta  # ty: ignore[unresolved-attribute]
    time_col = getattr(meta, "time_at", None)
    pk_cols = set(getattr(meta, "pk", ()))
    full_name = meta.name
    # Short name: strip dataset prefix (fitness__daily_hrv -> daily_hrv)
    short = full_name.split("__", 1)[-1] if "__" in full_name else full_name

    try:
        hints = get_type_hints(table_cls, include_extras=True)
        fields = dataclasses.fields(table_cls)
    except Exception:
        return []

    result: list[tuple[str, str, str]] = []
    for field in fields:
        col = field.name
        if col.startswith("_") or col in _SKIP_COLS or col == time_col:
            continue
        if col in pk_cols:
            continue

        hint = hints.get(col)
        field_meta = Field.from_hint(hint) if hint else None
        db_type = field_meta.db_type.lower() if field_meta else "varchar"

        # Explicit aggregation from Field metadata
        if field_meta and field_meta.aggregation:
            if field_meta.aggregation.lower() == "skip":
                continue
            agg_fn = field_meta.aggregation.upper()
        else:
            agg_fn = _AGG_MAP.get(db_type)
            if agg_fn is None:
                continue  # skip text, json, etc.

        result.append((agg_fn, col, f"{short}__{col}"))
    return result


def _has_dimensional_pk(table_cls: type) -> bool:
    """True if the PK contains columns beyond time + transform_id.

    Tables like finance__monthly_category have (month, category, transform_id)
    as PK -- the extra ``category`` dimension means rows can't be meaningfully
    aggregated into a single wide timeseries row per time bucket.
    """
    meta = table_cls._Meta  # ty: ignore[unresolved-attribute]
    time_col = getattr(meta, "time_at", None)
    pk = set(getattr(meta, "pk", ()))
    structural = {"transform_id", time_col} if time_col else {"transform_id"}
    return bool(pk - structural)


# ---------------------------------------------------------------------------
# SQL generation
# ---------------------------------------------------------------------------


def _time_cast_expr(time_col: str, db_type: str) -> str:
    """Build a SQL expression that casts a time column to TIMESTAMP.

    - DATE -> TRY_CAST("date" AS TIMESTAMP)
    - TIMESTAMP -> "start_at" (no cast needed)
    - VARCHAR (month 'YYYY-MM') -> TRY_CAST("month" || '-01' AS TIMESTAMP)
    """
    upper = db_type.upper()
    if upper == "DATE":
        return f'TRY_CAST("{time_col}" AS TIMESTAMP)'
    if "TIMESTAMP" in upper:
        return f'"{time_col}"'
    # VARCHAR month columns (e.g. 'YYYY-MM')
    return f"""TRY_CAST("{time_col}" || '-01' AS TIMESTAMP)"""


def _get_time_col_type(table_cls: type) -> tuple[str, str] | None:
    """Return (time_col_name, db_type) for a dataset table, or None."""
    meta = table_cls._Meta  # ty: ignore[unresolved-attribute]
    time_col = getattr(meta, "time_at", None)
    if not time_col:
        return None
    try:
        hints = get_type_hints(table_cls, include_extras=True)
        hint = hints.get(time_col)
        field_meta = Field.from_hint(hint) if hint else None
        if field_meta:
            return time_col, field_meta.db_type
    except Exception:
        pass
    return time_col, "TIMESTAMP"


def _build_base_sql(dataset_tables: list[type]) -> tuple[str, list[tuple[str, str, str]]] | None:
    """Build the 15-min base timeseries view SQL.

    Returns (sql, all_agg_columns) or None if no tables qualify.
    """
    ctes: list[str] = []
    cte_names: list[str] = []
    all_columns: list[tuple[str, str, str]] = []

    for table_cls in dataset_tables:
        if _has_dimensional_pk(table_cls):
            continue

        time_info = _get_time_col_type(table_cls)
        if not time_info:
            continue
        time_col, db_type = time_info

        agg_cols = _discover_agg_columns(table_cls)
        if not agg_cols:
            continue

        meta = table_cls._Meta  # ty: ignore[unresolved-attribute]
        full_name = meta.name
        short = full_name.split("__", 1)[-1] if "__" in full_name else full_name
        cte_name = f"cte_{short}"

        cast_expr = _time_cast_expr(time_col, db_type)
        bucket_expr = f"time_bucket(INTERVAL '15 minutes', {cast_expr})"

        cols_sql = ",\n    ".join(f'{agg_fn}("{col}") AS "{alias}"' for agg_fn, col, alias in agg_cols)

        cte_sql = (
            f"{cte_name} AS (\n"
            f"  SELECT {bucket_expr} AS time_bucket,\n"
            f"    {cols_sql}\n"
            f'  FROM "datasets"."{full_name}"\n'
            f"  GROUP BY 1\n"
            f")"
        )
        ctes.append(cte_sql)
        cte_names.append(cte_name)
        all_columns.extend(agg_cols)

    if not ctes:
        return None

    coalesce_expr = "COALESCE(" + ", ".join(f"{c}.time_bucket" for c in cte_names) + ") AS time_bucket"
    star_cols = ", ".join(f"{c}.* EXCLUDE (time_bucket)" for c in cte_names)

    first = cte_names[0]
    join_clauses = "\n".join(
        f"FULL OUTER JOIN {cte_name} ON {first}.time_bucket = {cte_name}.time_bucket" for cte_name in cte_names[1:]
    )

    cte_list = ",\n".join(ctes)
    sql = f"WITH {cte_list}\nSELECT {coalesce_expr}, {star_cols}\nFROM {first}\n{join_clauses}\nORDER BY time_bucket"

    return sql, all_columns


def _build_downsampled_sql(source_view: str, grain: str, columns: list[tuple[str, str, str]]) -> str:
    """Build a view that re-aggregates from a parent view at a coarser grain."""
    cols_sql = ",\n  ".join(f'{agg_fn}("{alias}") AS "{alias}"' for agg_fn, _col, alias in columns)
    return (
        f"SELECT date_trunc('{grain}', time_bucket) AS time_bucket,\n"
        f"  {cols_sql}\n"
        f'FROM "datasets"."{source_view}"\n'
        f"GROUP BY 1\n"
        f"ORDER BY 1"
    )


# ---------------------------------------------------------------------------
# View classes (DataView subclasses for catalog exposure)
# ---------------------------------------------------------------------------


def _make_view_class(name: str, display_name: str, description: str, sql: str) -> type[DataView]:
    """Create a DataView subclass for a timeseries view."""
    _sql = sql

    _Meta = type(
        "_Meta",
        (),
        {
            "name": name,
            "display_name": display_name,
            "description": description,
            "schema": DATASETS,
            "pk": (),
            "kind": "timeseries_view",
        },
    )

    return type(  # type: ignore[return-value]
        name.title().replace("_", ""),
        (DataView,),
        {
            "_Meta": _Meta,
            "_abstract": False,
            "_view_sql": classmethod(lambda cls: _sql),  # noqa: ARG005
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_VIEW_SPECS: list[tuple[str, str, str]] = [
    ("timeseries", "Timeseries (15min)", "All datasets joined at 15-minute grain."),
    ("timeseries_hourly", "Timeseries (hourly)", "All datasets aggregated to hourly grain."),
    ("timeseries_daily", "Timeseries (daily)", "All datasets aggregated to daily grain."),
    ("timeseries_weekly", "Timeseries (weekly)", "All datasets aggregated to weekly grain."),
    ("timeseries_monthly", "Timeseries (monthly)", "All datasets aggregated to monthly grain."),
    ("timeseries_yearly", "Timeseries (yearly)", "All datasets aggregated to yearly grain."),
]


def ensure_timeseries_views() -> None:
    """Create or replace all unified timeseries views in the datasets schema."""
    from app.database import cursor

    dataset_tables = _load_dataset_tables()
    if not dataset_tables:
        log.debug("No dataset tables found; skipping timeseries views")
        return

    result = _build_base_sql(dataset_tables)
    if result is None:
        log.debug("No aggregatable dataset tables; skipping timeseries views")
        return

    base_sql, all_columns = result

    # Build all view SQL statements
    view_sqls: dict[str, str] = {"timeseries": base_sql}
    for suffix, grain in _BASE_CHILDREN.items():
        view_sqls[f"timeseries_{suffix}"] = _build_downsampled_sql("timeseries", grain, all_columns)
    for suffix, grain in _DAILY_CHILDREN.items():
        view_sqls[f"timeseries_{suffix}"] = _build_downsampled_sql("timeseries_daily", grain, all_columns)

    # Create views in order (base first, then children)
    TIMESERIES_VIEWS.clear()
    with cursor() as cur:
        for view_name, display_name, description in _VIEW_SPECS:
            sql = view_sqls.get(view_name)
            if not sql:
                continue
            ddl = f'CREATE OR REPLACE VIEW "datasets"."{view_name}" AS {sql}'
            try:
                cur.execute(ddl)
                view_cls = _make_view_class(view_name, display_name, description, sql)
                TIMESERIES_VIEWS.append(view_cls)
            except Exception:
                log.exception("Failed to create view datasets.%s", view_name)

    log.info("Created %d timeseries views (%d columns)", len(TIMESERIES_VIEWS), len(all_columns))


def _load_dataset_tables() -> list[type]:
    """Discover all DatasetTable subclasses from installed datasets."""
    try:
        from shenas_datasets.core.dataset import Dataset

        tables: list[type] = []
        for dataset_cls in Dataset.load_all(include_internal=False):
            tables.extend(getattr(dataset_cls, "all_tables", ()))
        return tables
    except Exception:
        log.debug("Could not load dataset tables", exc_info=True)
        return []
