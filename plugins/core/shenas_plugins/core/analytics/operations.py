"""Curated operation vocabulary for LLM-driven recipes.

Each operation is a thin wrapper over Ibis. The wrapper:

1. Validates its inputs against the carrier ``RecipeNode``'s kind. The
   LLM cannot ``Lag`` a ``DimensionTable`` -- the validator rejects it
   before any SQL is generated.

2. Lowers to an :class:`ibis.Expr` via the underlying Ibis API. We own
   the wrapper API and the kind validation; Ibis owns the SQL
   generation.

3. Predicts its output kind so subsequent operations in the recipe can
   validate against it.

4. Returns a new ``RecipeNode``, never an unwrapped Ibis expression.

The five operations here are the v1 vocabulary. New operations are
added by humans, not by the LLM. The vocabulary is small enough to
fit in one Anthropic system prompt and large enough to express the
most common hypothesis shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import ibis

from shenas_plugins.core.analytics.node import RecipeNode


class OperationError(Exception):
    """Raised when an operation's parameters fail validation against its inputs."""


# ----------------------------------------------------------------------
# Time-series-shaped kinds: kinds where lag / rolling / resample are
# meaningful. Excludes SCD2 (dimension / snapshot / m2m_relation) and
# intervals (which would need overlap semantics, not point-in-time).
# ----------------------------------------------------------------------
_TIME_SERIES_KINDS: frozenset[str] = frozenset(
    {
        "event",
        "aggregate",
        "counter",
        "daily_metric",
        "weekly_metric",
        "monthly_metric",
        "event_metric",
    }
)

# Kinds that can be the *right* side of an AS-OF dimension join:
# anything with the SCD2 valid_from/valid_to columns.
_SCD2_KINDS: frozenset[str] = frozenset(
    {
        "dimension",
        "snapshot",
        "m2m_relation",
    }
)


@dataclass(frozen=True)
class Operation:
    """Abstract base. Concrete operations override ``apply``.

    Subclasses are :func:`@dataclass(frozen=True)` so they're hashable
    (used by recipe content-hash dedup later) and self-describing
    (the field names ARE the parameter schema for the LLM tool spec).

    The ``arity`` ClassVar declares how many ``RecipeNode`` inputs the
    operation consumes; the recipe compiler in ``recipe.py`` uses it to
    validate that DAG nodes wire the right number of upstream
    references. Most operations are arity-1; ``JoinAsOf`` is arity-2.
    """

    name: ClassVar[str]
    accepts: ClassVar[frozenset[str]] = frozenset()  # input kinds the op accepts
    arity: ClassVar[int] = 1

    def apply(self, *inputs: RecipeNode) -> RecipeNode:
        """Validate against the inputs' kinds and return a new ``RecipeNode``.

        Subclasses override with a fixed-arity signature
        (``apply(self, node)`` for arity 1, ``apply(self, left, right)``
        for arity 2). The recipe compiler always calls with positional
        args, so Python's standard argument binding handles it.
        """
        raise NotImplementedError

    def _check_kind(self, node: RecipeNode) -> None:
        if self.accepts and node.kind not in self.accepts:
            msg = f"{self.name}: cannot apply to a `{node.kind}` table (accepts: {sorted(self.accepts)})"
            raise OperationError(msg)


# ----------------------------------------------------------------------
# Lag: shift a column by N periods along the time axis.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Lag(Operation):
    """Compute a lagged version of ``column`` by ``n`` periods.

    Adds a new column ``<column>_lag<n>`` to the carrier. The order
    column defaults to ``RecipeNode.time_at()`` -- override with
    ``order_by`` if the table has multiple candidate time columns.

    Examples
    --------
    >>> Lag("caffeine_mg", n=1).apply(daily_intake_node)
    """

    column: str
    n: int = 1
    order_by: str | None = None
    partition_by: tuple[str, ...] = ()

    name: ClassVar[str] = "lag"
    accepts: ClassVar[frozenset[str]] = _TIME_SERIES_KINDS

    def apply(self, node: RecipeNode) -> RecipeNode:
        self._check_kind(node)
        order_col = self.order_by or node.time_at()
        if not order_col:
            msg = f"lag: no order_by specified and {node.table_ref} has no time_at column"
            raise OperationError(msg)
        if self.column not in node.expr.columns:
            msg = f"lag: column `{self.column}` not in {node.table_ref}"
            raise OperationError(msg)

        window_kwargs: dict[str, Any] = {"order_by": order_col}
        if self.partition_by:
            window_kwargs["group_by"] = list(self.partition_by)
        win = ibis.window(**window_kwargs)

        new_col_name = f"{self.column}_lag{self.n}"
        new_expr = node.expr.mutate(**{new_col_name: node.expr[self.column].lag(self.n).over(win)})
        return node.with_expr(new_expr)


# ----------------------------------------------------------------------
# Rolling: rolling window aggregation.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Rolling(Operation):
    """Compute a rolling window aggregation over ``column``.

    Adds a new column ``<column>_<fn><window>`` (e.g. ``hr_avg7``).
    Trailing window: includes the current row and the previous
    ``window-1`` rows.

    Supported aggregations: ``avg``, ``sum``, ``min``, ``max``.
    """

    column: str
    window: int
    fn: str = "avg"
    order_by: str | None = None
    partition_by: tuple[str, ...] = ()

    name: ClassVar[str] = "rolling"
    accepts: ClassVar[frozenset[str]] = _TIME_SERIES_KINDS

    _SUPPORTED_FNS: ClassVar[frozenset[str]] = frozenset({"avg", "sum", "min", "max"})

    def apply(self, node: RecipeNode) -> RecipeNode:
        self._check_kind(node)
        if self.fn not in self._SUPPORTED_FNS:
            msg = f"rolling: unsupported fn `{self.fn}`; choose one of {sorted(self._SUPPORTED_FNS)}"
            raise OperationError(msg)
        if self.window < 1:
            msg = f"rolling: window must be >= 1, got {self.window}"
            raise OperationError(msg)
        order_col = self.order_by or node.time_at()
        if not order_col:
            msg = f"rolling: no order_by specified and {node.table_ref} has no time_at column"
            raise OperationError(msg)
        if self.column not in node.expr.columns:
            msg = f"rolling: column `{self.column}` not in {node.table_ref}"
            raise OperationError(msg)

        window_kwargs: dict[str, Any] = {
            "order_by": order_col,
            "preceding": self.window - 1,
            "following": 0,
        }
        if self.partition_by:
            window_kwargs["group_by"] = list(self.partition_by)
        win = ibis.window(**window_kwargs)

        col_expr = node.expr[self.column]
        agg = {"avg": col_expr.mean, "sum": col_expr.sum, "min": col_expr.min, "max": col_expr.max}[self.fn]
        new_col_name = f"{self.column}_{self.fn}{self.window}"
        new_expr = node.expr.mutate(**{new_col_name: agg().over(win)})
        return node.with_expr(new_expr)


# ----------------------------------------------------------------------
# Resample: roll a fine-grained table up to a coarser time grain.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Resample(Operation):
    """Roll up a time-series table to a coarser grain.

    Groups rows by truncated time bucket (``day`` / ``week`` / ``month``)
    plus any explicit ``group_by`` columns, then aggregates the named
    columns. The result is one row per bucket per group with column
    naming ``<column>_<fn>``.

    The output kind shifts to the matching ``*_metric`` family
    (``daily_metric`` / ``weekly_metric`` / ``monthly_metric``).
    """

    grain: str  # "day" | "week" | "month"
    aggregations: tuple[tuple[str, str], ...] = ()  # ((column, fn), ...) where fn in {"avg", "sum", "min", "max", "count"}
    group_by: tuple[str, ...] = ()
    time_at: str | None = None  # override the carrier's time_at column

    name: ClassVar[str] = "resample"
    accepts: ClassVar[frozenset[str]] = _TIME_SERIES_KINDS

    _GRAIN_TO_KIND: ClassVar[dict[str, str]] = {
        "day": "daily_metric",
        "week": "weekly_metric",
        "month": "monthly_metric",
    }
    _AGG_FNS: ClassVar[frozenset[str]] = frozenset({"avg", "sum", "min", "max", "count"})

    def apply(self, node: RecipeNode) -> RecipeNode:
        self._check_kind(node)
        if self.grain not in self._GRAIN_TO_KIND:
            msg = f"resample: grain must be one of {sorted(self._GRAIN_TO_KIND)}; got `{self.grain}`"
            raise OperationError(msg)
        time_col = self.time_at or node.time_at()
        if not time_col:
            msg = f"resample: no time_at specified and {node.table_ref} has no time_at column"
            raise OperationError(msg)
        if not self.aggregations:
            msg = "resample: at least one aggregation required"
            raise OperationError(msg)
        for col, fn in self.aggregations:
            if col not in node.expr.columns:
                msg = f"resample: column `{col}` not in {node.table_ref}"
                raise OperationError(msg)
            if fn not in self._AGG_FNS:
                msg = f"resample: unsupported agg fn `{fn}`; choose one of {sorted(self._AGG_FNS)}"
                raise OperationError(msg)

        bucket_col_name = self.grain  # "day" / "week" / "month"
        bucket_expr = node.expr[time_col].truncate(self.grain[0])  # 'D' / 'W' / 'M'
        bucketed = node.expr.mutate(**{bucket_col_name: bucket_expr})

        agg_exprs: dict[str, Any] = {}
        for col, fn in self.aggregations:
            col_expr = bucketed[col]
            method = {
                "avg": col_expr.mean,
                "sum": col_expr.sum,
                "min": col_expr.min,
                "max": col_expr.max,
                "count": col_expr.count,
            }[fn]
            agg_exprs[f"{col}_{fn}"] = method()

        group_cols = [bucket_col_name, *self.group_by]
        new_expr = bucketed.group_by(group_cols).agg(**agg_exprs)
        new_kind = self._GRAIN_TO_KIND[self.grain]
        return RecipeNode(
            expr=new_expr,
            kind=new_kind,
            time_columns={"time_at": bucket_col_name},
            table_ref=node.table_ref,
        )


# ----------------------------------------------------------------------
# JoinAsOf: temporal left join. The right side is typically an SCD2
# dimension or another time-series table on a coarser grain.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class JoinAsOf(Operation):
    """Temporal left join: for each left row at ``ts``, find the most
    recent right row whose ``on`` column is ``<= ts``.

    Used for two distinct cases:

    1. **Fact -> SCD2 dimension**: e.g. join an event stream to a
       dimension table whose values change over time. The right side's
       kind must be one of ``dimension`` / ``snapshot`` / ``m2m_relation``.

    2. **Time-series -> time-series**: e.g. join two ``daily_metric``
       tables on the same date column to compare them.

    Both sides must agree on the ``on`` column type and name.

    Arity 2: ``apply(left, right)``. The recipe compiler wires the two
    upstream nodes from the DAG by name; standalone callers pass them
    positionally.
    """

    on: str  # time-axis column name on both sides
    by: tuple[str, ...] = ()  # additional equality predicates ("partition" cols)

    name: ClassVar[str] = "join_as_of"
    accepts: ClassVar[frozenset[str]] = _TIME_SERIES_KINDS | _SCD2_KINDS
    arity: ClassVar[int] = 2

    def apply(self, left: RecipeNode, right: RecipeNode) -> RecipeNode:  # type: ignore[override]
        self._check_kind(left)
        if self.on not in left.expr.columns:
            msg = f"join_as_of: `{self.on}` not in left side ({left.table_ref})"
            raise OperationError(msg)
        if self.on not in right.expr.columns:
            msg = f"join_as_of: `{self.on}` not in right side ({right.table_ref})"
            raise OperationError(msg)

        # Ibis 12's asof_join takes the time column as positional ``on`` and
        # additional equality predicates as positional ``predicates``.
        if self.by:
            joined = left.expr.asof_join(right.expr, on=self.on, predicates=list(self.by))
        else:
            joined = left.expr.asof_join(right.expr, on=self.on)
        # Output kind = left side's kind (the join enriches the left rows
        # with right-side columns; row count and time semantics don't
        # change).
        return left.with_expr(joined)


# ----------------------------------------------------------------------
# Correlate: a single-scalar Pearson correlation between two columns.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Correlate(Operation):
    """Pearson correlation coefficient between two columns of the carrier.

    Returns a node with a one-row aggregation: ``{corr: float}``.
    Use after a ``JoinAsOf`` (or any other op) that puts both columns
    on the same row.

    DuckDB's correlation is the *population* correlation (``corr_pop``);
    Ibis maps ``how="pop"`` to it. Sample correlation is unsupported on
    DuckDB and we don't expose it -- the difference is negligible at
    typical hypothesis-testing N values.
    """

    x: str
    y: str
    group_by: tuple[str, ...] = ()

    name: ClassVar[str] = "correlate"
    # Correlation works on any node that has both numeric columns; the
    # kind doesn't constrain it.
    accepts: ClassVar[frozenset[str]] = frozenset()  # empty = accept anything

    def apply(self, node: RecipeNode) -> RecipeNode:
        if self.x not in node.expr.columns:
            msg = f"correlate: `{self.x}` not in {node.table_ref}"
            raise OperationError(msg)
        if self.y not in node.expr.columns:
            msg = f"correlate: `{self.y}` not in {node.table_ref}"
            raise OperationError(msg)

        corr_expr = node.expr[self.x].corr(node.expr[self.y], how="pop")
        if self.group_by:
            new_expr = node.expr.group_by(list(self.group_by)).agg(corr=corr_expr)
        else:
            new_expr = node.expr.aggregate(corr=corr_expr)

        # The output is a small aggregation, no longer a time-series.
        # Tag it as a generic "scalar_result" so downstream ops know
        # there's nothing more to lag / window / resample.
        return RecipeNode(
            expr=new_expr,
            kind="scalar_result",
            time_columns={},
            table_ref=node.table_ref,
        )


# ----------------------------------------------------------------------
# Registry of operations available to the LLM. Adding to this list is
# the only way to expand the vocabulary -- the LLM cannot invent new
# operations at runtime.
# ----------------------------------------------------------------------

OPERATIONS: tuple[type[Operation], ...] = (Lag, Rolling, Resample, JoinAsOf, Correlate)
