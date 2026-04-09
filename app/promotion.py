"""Promote a hypothesis into a canonical MetricTable.

Promotion is the only path that writes canonical state. Until a user
explicitly promotes a hypothesis, every analytical transformation is
transient -- the recipe lives only on the hypothesis row, the result
is cached but not load-bearing, and re-running the recipe is always
possible from the row alone.

Storage model
-------------
Promoted metrics are **deployment state**, not code. Each promotion
inserts one row into ``shenas_system.promoted_metrics`` capturing the
recipe (frozen at promotion time), the column shape, and the
provenance back to the originating hypothesis. At catalog-walk time
:func:`shenas_datasets.promoted.PromotedSchema.all_tables` walks that
table and constructs a ``MetricTable`` subclass per row via
``type()`` -- the same machinery ``Source.__init_subclass__`` already
uses to build per-pipe ``Config`` / ``Auth`` classes.

The constructed class's ``transform(con)`` classmethod re-runs the
frozen recipe on every Source.sync() and replaces the table contents.

Why no generated Python files
-----------------------------
Promotion is a click in the UI, not a code change. Treating it as code
would mean generated source files on disk, brittle string-formatting,
no review story, and the wrong place for provenance. Treating it as
data means re-promotion is ``UPDATE``, delete is ``DELETE``, and the
row participates in the encrypted-DB lifecycle like every other system
fact.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.hypotheses import Hypothesis


class ColumnSpec(BaseModel):
    name: str
    db_type: str


class PromotionResult(BaseModel):
    name: str
    schema_: str
    hypothesis_id: int
    qualified: str


def _validate_name(name: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        msg = f"promoted metric name must be snake_case (got {name!r})"
        raise ValueError(msg)
    return name


def _columns_from_result(hypothesis: Hypothesis) -> tuple[list[ColumnSpec], list[str]]:
    """Derive (columns, pk) from the hypothesis's cached result.

    Returns ``([ColumnSpec, ...], [pk_col, ...])``.
    Falls back to a single ``value`` column when the hypothesis has
    never been run or the result shape is opaque. The dataclass fields
    on the eventual ``MetricTable`` subclass are derived from this.
    """
    columns: list[ColumnSpec] = []
    pk: list[str] = []
    result = hypothesis.result()
    if result is not None:
        kind = getattr(result, "type", None)
        if kind == "table":
            for col in getattr(result, "columns", []) or []:
                columns.append(ColumnSpec(name=col, db_type="VARCHAR"))
                if col in ("date", "source"):
                    pk.append(col)
        elif kind == "scalar":
            columns.append(ColumnSpec(name="value", db_type="DOUBLE"))
    if not columns:
        columns.append(ColumnSpec(name="value", db_type="VARCHAR"))
    if not pk:
        pk = ["id"]
        columns.insert(0, ColumnSpec(name="id", db_type="INTEGER"))
    return columns, pk


def promote_hypothesis(
    hypothesis: Hypothesis,
    *,
    name: str,
    metric_schema: str = "metrics",
) -> PromotionResult:
    """Insert a row into ``shenas_system.promoted_metrics``.

    Returns the persisted row as a dict so callers (the GraphQL
    mutation, tests) can confirm what landed. The hypothesis is also
    marked promoted via :meth:`Hypothesis.mark_promoted` so the
    breadcrumb is on both rows.
    """
    _validate_name(name)
    if not hypothesis.recipe_json:
        msg = "cannot promote a hypothesis with no recipe"
        raise ValueError(msg)

    from shenas_datasets.promoted import PromotedMetric

    if PromotedMetric.find(name, metric_schema) is not None:
        msg = f"promoted metric {metric_schema}.{name} already exists"
        raise ValueError(msg)

    columns, pk = _columns_from_result(hypothesis)
    record = PromotedMetric(
        name=name,
        metric_schema=metric_schema,
        recipe_json=hypothesis.recipe_json,
        inputs=hypothesis.inputs or "",
        columns_json=json.dumps([c.model_dump() for c in columns]),
        pk_json=json.dumps(pk),
        hypothesis_id=hypothesis.id,
        question=hypothesis.question or "",
    )
    record.insert()
    hypothesis.mark_promoted(f"{metric_schema}.{name}")
    return PromotionResult(
        name=record.name,
        schema_=record.metric_schema,
        hypothesis_id=record.hypothesis_id,
        qualified=f"{record.metric_schema}.{record.name}",
    )
