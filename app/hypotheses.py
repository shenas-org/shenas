"""Hypothesis: persistent record of an LLM-driven analytical investigation.

A :class:`Hypothesis` is the durable artifact of an LLM-authored
investigation: the user's natural-language question, the LLM's plan,
the recipe DAG it constructed, the inputs it referenced, the result it
observed, and the LLM's interpretation. One row per hypothesis, stored
in ``shenas_system.hypotheses``.

Recipe and result are JSON-serialized into ``recipe_json`` and
``result_json`` columns. The recipe is reconstructed via
:meth:`Hypothesis.recipe` on demand; the result is cached but **not**
the source of truth -- the recipe is. Re-opening a hypothesis can
either read the cached result or replay the recipe against current data.

Promotion is the bridge from a hypothesis to a canonical metric table:
when the user explicitly says "save this analysis as a permanent
metric," the recipe gets converted into a ``MetricTable`` subclass and
``promoted_to`` captures the qualified name of the new metric.
**Promotion is the only path that creates canonical state**; until
promotion, every analytical transformation is transient.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    from shenas_plugins.core.analytics import Recipe, Result


@dataclass
class Hypothesis(Table):
    """One LLM-authored investigation, end to end.

    Stored as a row in ``shenas_system.hypotheses``. The class itself is
    the dataclass for that row -- there's no separate wrapper. CRUD
    comes from the :class:`Table` ABC; the only hypothesis-specific
    methods are the lazy JSON decoders for recipe / result and the
    :meth:`create` factory that handles serialization.
    """

    table_name: ClassVar[str] = "hypotheses"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Hypotheses"
    table_description: ClassVar[str | None] = "LLM-authored hypothesis records: question, recipe, result, interpretation."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Hypothesis ID", db_default="nextval('shenas_system.hypothesis_seq')"),
    ] = 0
    question: Annotated[str, Field(db_type="TEXT", description="The user's natural-language question")] = ""
    plan: (
        Annotated[
            str,
            Field(db_type="TEXT", description="LLM's natural-language plan for answering it", db_default="''"),
        ]
        | None
    ) = None
    recipe_json: Annotated[
        str,
        Field(db_type="TEXT", description="The Recipe DAG as JSON (SourceRefs + OpCalls)"),
    ] = ""
    inputs: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Comma-separated qualified table names referenced by the recipe",
                db_default="''",
            ),
        ]
        | None
    ) = None
    result_json: (
        Annotated[
            str,
            Field(db_type="TEXT", description="The Result tagged-union as JSON (most recent run)", db_default="''"),
        ]
        | None
    ) = None
    interpretation: (
        Annotated[
            str,
            Field(db_type="TEXT", description="LLM's narrative interpretation of the result", db_default="''"),
        ]
        | None
    ) = None
    created_at: (
        Annotated[
            str,
            Field(db_type="TIMESTAMP", description="When this hypothesis was created", db_default="current_timestamp"),
        ]
        | None
    ) = None
    model: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="LLM provider@model@temperature that authored the recipe",
                db_default="''",
            ),
        ]
        | None
    ) = None
    promoted_to: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Qualified metric name if this hypothesis was promoted to a canonical MetricTable",
            ),
        ]
        | None
    ) = None

    # ------------------------------------------------------------------
    # Factory: create() handles recipe serialization + input extraction
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        question: str,
        recipe: Recipe,
        *,
        plan: str = "",
        model: str = "",
    ) -> Hypothesis:
        """Create a new hypothesis row from a question + a Recipe.

        Result and interpretation are blank initially -- call
        :meth:`attach_result` and :meth:`attach_interpretation` after
        running the recipe.
        """
        h = cls(
            question=question,
            plan=plan,
            recipe_json=_serialize_recipe(recipe),
            inputs=",".join(sorted(_extract_input_tables(recipe))),
            model=model,
        )
        return h.insert()

    # ------------------------------------------------------------------
    # Recipe / Result accessors -- deserialize JSON columns lazily.
    # ------------------------------------------------------------------

    def recipe(self) -> Recipe:
        """Reconstruct the :class:`Recipe` from ``recipe_json``."""
        from shenas_plugins.core.analytics import OpCall, Recipe, SourceRef

        payload = json.loads(self.recipe_json)
        nodes: dict[str, SourceRef | OpCall] = {}
        for name, node in payload["nodes"].items():
            if node.get("type") == "source":
                nodes[name] = SourceRef(table=node["table"])
            else:
                nodes[name] = OpCall(
                    op_name=node["op_name"],
                    params=node.get("params", {}),
                    inputs=tuple(node.get("inputs", ())),
                )
        return Recipe(nodes=nodes, final=payload["final"])

    def result(self) -> Result | None:
        """Reconstruct the most recent :class:`Result` from ``result_json``,
        or ``None`` if the recipe hasn't been executed yet."""
        from shenas_plugins.core.analytics import ErrorResult, ScalarResult, TableResult

        raw = self.result_json
        if not raw:
            return None
        payload = json.loads(raw)
        kind = payload.get("type")
        if kind == "scalar":
            return ScalarResult(
                value=payload.get("value"),
                column=payload.get("column", ""),
                elapsed_ms=payload.get("elapsed_ms", 0.0),
                sql=payload.get("sql", ""),
            )
        if kind == "table":
            return TableResult(
                rows=payload.get("rows", []),
                columns=payload.get("columns", []),
                row_count=payload.get("row_count", 0),
                truncated=payload.get("truncated", False),
                elapsed_ms=payload.get("elapsed_ms", 0.0),
                sql=payload.get("sql", ""),
            )
        if kind == "error":
            return ErrorResult(
                message=payload.get("message", ""),
                kind=payload.get("kind", "execution"),
                elapsed_ms=payload.get("elapsed_ms", 0.0),
                sql=payload.get("sql", ""),
            )
        return None

    # ------------------------------------------------------------------
    # Convenience mutators -- thin wrappers over .save()
    # ------------------------------------------------------------------

    def attach_result(self, result: Result) -> Hypothesis:
        """Attach a freshly-computed Result to this hypothesis."""
        self.result_json = _serialize_result(result)
        return self.save()

    def attach_interpretation(self, interpretation: str) -> Hypothesis:
        """Attach the LLM's narrative interpretation."""
        self.interpretation = interpretation
        return self.save()

    def mark_promoted(self, qualified_metric_name: str) -> Hypothesis:
        """Record that this hypothesis was promoted to a canonical metric table.

        The actual class generation + materialization happens elsewhere
        (Phase 3, PR 3.1). This is just the breadcrumb on the row.
        """
        self.promoted_to = qualified_metric_name
        return self.save()


# ----------------------------------------------------------------------
# Recipe / Result JSON serialization helpers
# ----------------------------------------------------------------------


def _serialize_recipe(recipe: Recipe) -> str:
    """Serialize a Recipe DAG to JSON.

    Lives here rather than on Recipe so the analytics package stays
    free of "how to persist" concerns. Format mirrors what
    :meth:`Hypothesis.recipe` deserializes.
    """
    from shenas_plugins.core.analytics import OpCall, SourceRef

    nodes: dict[str, dict[str, Any]] = {}
    for name, node in recipe.nodes.items():
        if isinstance(node, SourceRef):
            nodes[name] = {"type": "source", "table": node.table}
        elif isinstance(node, OpCall):
            nodes[name] = {
                "type": "op",
                "op_name": node.op_name,
                "params": dict(node.params),
                "inputs": list(node.inputs),
            }
    return json.dumps({"nodes": nodes, "final": recipe.final})


def _serialize_result(result: Result) -> str:
    """Serialize a Result tagged union to JSON via its ``to_dict()``."""
    return json.dumps(result.to_dict())


def _extract_input_tables(recipe: Recipe) -> list[str]:
    """Return the qualified names of every SourceRef in the recipe.

    Persisted in the ``inputs`` column so the future "what depends on
    table X?" query is a simple LIKE -- no need to deserialize the
    recipe JSON.
    """
    from shenas_plugins.core.analytics import SourceRef

    return [node.table for node in recipe.nodes.values() if isinstance(node, SourceRef)]
