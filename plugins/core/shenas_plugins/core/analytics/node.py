"""``RecipeNode`` -- the typed carrier passed between operations.

A node holds a private :class:`ibis.Expr` plus the metadata an operation
needs to validate its inputs (the table's kind, the time-axis column,
the originating qualified name). Operations consume one or more nodes
and return a new node, never an unwrapped Ibis expression -- this is the
guardrail that keeps recipe authors (humans or LLMs) inside the curated
vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import ibis.expr.types as it


@dataclass(frozen=True)
class RecipeNode:
    """A typed Ibis expression carrying metadata about its source table.

    Attributes
    ----------
    expr
        The underlying ``ibis.Expr`` (typically an ``ibis.Table``). Held
        privately by convention -- recipe authors shouldn't reach inside
        and call arbitrary Ibis methods. Operations are the only public
        way to transform a node.
    kind
        The kind string (``"event"`` / ``"interval"`` / ``"daily_metric"`` /
        etc.) that operations validate against. Propagates through
        operations: ``Lag(EventTable)`` produces a node still tagged
        ``"event"``; ``Resample(EventTable, "week")`` produces one tagged
        ``"weekly_metric"``.
    time_columns
        The time-axis columns the operations need: ``time_at`` for
        events / aggregates / metrics, ``time_start`` + ``time_end`` for
        intervals. Lifted from ``Table.table_metadata()['time_columns']``
        on the source table at recipe-build time.
    table_ref
        Qualified ``"<schema>.<table>"`` name of the originating table.
        Pure provenance -- shown to the user in "show your work" UIs and
        carried into the hypothesis record.
    """

    expr: it.Expr
    kind: str
    time_columns: dict[str, Any] = field(default_factory=dict)
    table_ref: str = ""

    def time_at(self) -> str | None:
        """The single time-axis column for events / aggregates / metrics.

        Operations like ``Lag`` and ``Rolling`` use this when the user
        doesn't specify ``order_by`` explicitly. Returns ``None`` for
        kinds that don't have a single ``time_at`` column (intervals,
        SCD2 dimensions).
        """
        return self.time_columns.get("time_at")

    def with_expr(self, new_expr: it.Expr, *, kind: str | None = None) -> RecipeNode:
        """Return a copy of this node with a new expression and (optionally) a new kind.

        Used by operations to produce their output without losing the
        ``time_columns`` and ``table_ref`` provenance.
        """
        return RecipeNode(
            expr=new_expr,
            kind=kind if kind is not None else self.kind,
            time_columns=self.time_columns,
            table_ref=self.table_ref,
        )
