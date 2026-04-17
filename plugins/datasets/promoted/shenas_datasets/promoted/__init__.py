"""Promoted hypothesis metrics dataset.

This package owns the ``PromotedMetric`` row class plus the
``PromotedSchema`` dataset that fronts it. Promoted metrics are
**deployment state**, not generated source files: each one is a row in
``analysis.promoted_metrics`` capturing the frozen recipe, the
column shape, and the provenance back to the originating hypothesis.

At catalog-walk time :meth:`PromotedSchema.all_tables` queries the row
table and constructs a ``MetricTable`` subclass per row via ``type()``.
The constructed class carries:

- ``_Meta``  with name / schema / pk derived from the row
- dataclass fields synthesized from ``columns_json``
- a ``transform(con)`` classmethod that closes over the row's
  ``recipe_json`` and re-runs it on every Source.sync()
- ``promoted_from_hypothesis`` / ``derived_from`` / ``derived_via``
  ClassVars for provenance

There are no Python source files for promoted metrics on disk. Re-
promotion is ``UPDATE``, deletion is ``DELETE``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Any

from app.schema import ANALYSIS
from app.table import Field, Table
from shenas_datasets.core import Dataset, MetricTable


@dataclass
class PromotedMetric(Table):
    """One row per promoted hypothesis. Lives in analysis.promoted_metrics."""

    class _Meta:
        name = "promoted_metrics"
        display_name = "Promoted Metrics"
        description = "Hypotheses promoted to canonical metric tables."
        schema = ANALYSIS
        pk = ("name", "metric_schema")

    name: Annotated[str, Field(db_type="VARCHAR", description="snake_case metric name")] = ""
    metric_schema: Annotated[str, Field(db_type="VARCHAR", description="DuckDB schema for the materialized table")] = "metrics"
    recipe_json: Annotated[str, Field(db_type="TEXT", description="Recipe DAG, frozen at promotion time")] = ""
    inputs: Annotated[str, Field(db_type="VARCHAR", description="Comma-separated input table names", db_default="''")] = ""
    columns_json: Annotated[
        str, Field(db_type="TEXT", description="JSON list of {name, db_type} for the materialized columns")
    ] = "[]"
    pk_json: Annotated[str, Field(db_type="TEXT", description="JSON list of pk column names")] = "[]"
    hypothesis_id: Annotated[int, Field(db_type="INTEGER", description="Source hypothesis id")] = 0
    question: Annotated[str, Field(db_type="TEXT", description="Original question (for display)", db_default="''")] | None = (
        None
    )
    created_at: (
        Annotated[
            str,
            Field(db_type="TIMESTAMP", description="When this metric was promoted", db_default="current_timestamp"),
        ]
        | None
    ) = None


_DUCKDB_TO_PYTHON: dict[str, type] = {
    "VARCHAR": str,
    "TEXT": str,
    "INTEGER": int,
    "BIGINT": int,
    "DOUBLE": float,
    "REAL": float,
    "BOOLEAN": bool,
    "DATE": str,
    "TIMESTAMP": str,
}


def _make_promoted_class(record: PromotedMetric) -> type[MetricTable]:
    """Build a MetricTable subclass for one PromotedMetric row.

    Uses ``type()`` -- same machinery as ``Source.__init_subclass__``
    when it builds per-source ``Config`` / ``Auth`` classes. The
    constructed class is a real ``MetricTable`` peer of the
    hand-written canonical metrics, just synthesized from data instead
    of declared in source.
    """
    columns = json.loads(record.columns_json or "[]")
    pk = tuple(json.loads(record.pk_json or "[]")) or ("id",)

    annotations: dict[str, Any] = {}
    defaults: dict[str, Any] = {}
    for col in columns:
        col_name = col["name"]
        py_type = _DUCKDB_TO_PYTHON.get(col["db_type"].upper(), str)
        annotations[col_name] = Annotated[
            py_type | None,  # ty: ignore[invalid-type-form]
            Field(db_type=col["db_type"], description=f"Promoted column from recipe (#{record.hypothesis_id})"),
        ]
        defaults[col_name] = None

    cls_name = "".join(part.title() for part in record.name.split("_")) or "PromotedMetric"
    meta_cls = type(
        "_Meta",
        (object,),
        {
            "name": record.name,
            "display_name": cls_name,
            "description": record.question or f"Promoted from hypothesis #{record.hypothesis_id}",
            "schema": record.metric_schema,
            "pk": pk,
        },
    )

    namespace: dict[str, Any] = {
        "_Meta": meta_cls,
        "promoted_from_hypothesis": record.hypothesis_id,
        "derived_from": (record.inputs or "").split(",") if record.inputs else [],
        "derived_via": record.recipe_json or "",
        "__annotations__": annotations,
        "transform": classmethod(_make_transform(record)),
        **defaults,
    }
    return type(cls_name, (MetricTable,), namespace)


def _make_transform(record: PromotedMetric):
    """Build the transform(con) classmethod for one promoted metric row.

    Closes over ``recipe_json`` so the constructed class carries
    everything it needs to refresh itself.
    """
    recipe_json = record.recipe_json

    def transform(cls, con) -> int:
        from shenas_analyses.core.analytics import (
            OpCall,
            Recipe,
            SourceRef,
            TableResult,
            run_recipe,
        )

        from app.data_catalog import catalog as get_catalog
        from app.database import analytics_backend

        payload = json.loads(recipe_json)
        nodes: dict[str, SourceRef | OpCall] = {}
        for node_name, node in payload.get("nodes", {}).items():
            if node.get("type") == "source":
                nodes[node_name] = SourceRef(table=node["table"])
            else:
                nodes[node_name] = OpCall(
                    op_name=node.get("op_name", ""),
                    params=node.get("params", {}),
                    inputs=tuple(node.get("inputs", ())),
                )
        recipe = Recipe(nodes=nodes, final=payload.get("final", ""))
        result = run_recipe(recipe, get_catalog().metadata_by_id(), backend=analytics_backend())
        if not isinstance(result, TableResult):
            return 0
        cls.clear_rows()
        if not result.rows:
            return 0
        qualified = f'"{cls._Meta.schema}"."{cls._Meta.name}"'
        col_list = ", ".join('"' + c.replace('"', '""') + '"' for c in result.columns)
        placeholders = ", ".join(["?"] * len(result.columns))
        for row in result.rows:
            con.execute(
                f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})",
                [row.get(c) for c in result.columns],
            )
        return len(result.rows)

    return transform


def _discover_promoted_classes() -> list[type[MetricTable]]:
    """Walk analysis.promoted_metrics and synthesize one class per row.

    Returns ``[]`` if the row table doesn't exist yet (e.g. during
    bootstrap, before ``_ensure_system_tables`` has run). Catalog
    consumers and ``Dataset.metadata()`` re-query on every access so
    newly-promoted metrics show up without restarting the app.
    """
    try:
        rows = PromotedMetric.all()
    except Exception:
        return []
    return [_make_promoted_class(r) for r in rows]


class _AllTablesDescriptor:
    """Class-level descriptor that re-queries promoted metrics on each access.

    Promoted metrics are deployment state -- they appear / disappear at
    runtime as users click Promote in the UI. The dataset interface
    expects ``cls.all_tables`` to be iterable; this descriptor makes
    every access return the current synthesized class list.
    """

    def __get__(self, instance: object, owner: type | None = None) -> list[type[MetricTable]]:
        return _discover_promoted_classes()


class PromotedSchema(Dataset):
    name = "promoted"
    display_name = "Promoted Hypotheses"
    description = "Canonical metric tables synthesized from promoted hypotheses."
    primary_table = ""

    # Re-queries the promoted_metrics row table on every access.
    all_tables = _AllTablesDescriptor()  # type: ignore[assignment]


__all__ = ["PromotedMetric", "PromotedSchema"]
