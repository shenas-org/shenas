"""Hypothesis: persistent record of an LLM-driven analytical investigation.

A :class:`Hypothesis` is the durable artifact of an LLM-authored
investigation: the user's natural-language question, the LLM's plan,
the recipe DAG it constructed, the inputs it referenced, the result it
observed, and the LLM's interpretation. One row per hypothesis, stored
in ``analysis.hypotheses``.

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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from app.schema import ANALYSIS
from app.table import Field, Table

if TYPE_CHECKING:
    from shenas_analyses.core.analytics import Recipe, Result


@dataclass
class Hypothesis(Table):
    """One LLM-authored investigation, end to end.

    Stored as a row in ``analysis.hypotheses``. The class itself is
    the dataclass for that row -- there's no separate wrapper. CRUD
    comes from the :class:`Table` ABC; the only hypothesis-specific
    methods are the lazy JSON decoders for recipe / result and the
    :meth:`create` factory that handles serialization.
    """

    class _Meta:
        name = "hypotheses"
        display_name = "Hypotheses"
        description = "LLM-authored hypothesis records: question, recipe, result, interpretation."
        schema = ANALYSIS
        pk = ("id",)
        sequences = ("analysis.hypothesis_seq",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Hypothesis ID", db_default="nextval('analysis.hypothesis_seq')"),
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
    # Cost / latency tracking
    llm_input_tokens: Annotated[int, Field(db_type="INTEGER", description="LLM input tokens consumed")] | None = None
    llm_output_tokens: Annotated[int, Field(db_type="INTEGER", description="LLM output tokens generated")] | None = None
    llm_elapsed_ms: Annotated[float, Field(db_type="DOUBLE", description="Total wall-clock LLM time in ms")] | None = None
    query_elapsed_ms: (
        Annotated[float, Field(db_type="DOUBLE", description="Total wall-clock query execution time in ms")] | None
    ) = None
    wall_clock_ms: (
        Annotated[float, Field(db_type="DOUBLE", description="End-to-end wall clock for the whole askHypothesis turn")] | None
    ) = None
    # Analysis mode used for this hypothesis (e.g. "hypothesis", "rca", "forecast").
    mode: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Analysis mode used (e.g. hypothesis, rca, forecast)",
                db_default="'hypothesis'",
            ),
        ]
        | None
    ) = None
    # Forking: parent_id is the hypothesis this one was branched from.
    # Forks share the question + initial recipe but iterate independently.
    parent_id: Annotated[int, Field(db_type="INTEGER", description="Parent hypothesis id if this is a fork")] | None = None
    is_suggested: (
        Annotated[bool, Field(db_type="BOOLEAN", description="LLM-suggested analysis, not yet accepted", db_default="FALSE")]
        | None
    ) = None

    # ------------------------------------------------------------------
    # Suggestion lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def create_suggestion(
        cls,
        question: str,
        *,
        rationale: str = "",
        datasets_involved: str = "",
        complexity: str = "",
        model: str = "",
    ) -> Hypothesis:
        """Create a suggested hypothesis (question only, no recipe)."""
        from shenas_analyses.core.analytics import Recipe

        empty = Recipe(nodes={}, final="")
        h = cls(
            question=question,
            plan=rationale,
            recipe_json=_serialize_recipe(empty),
            inputs=datasets_involved,
            model=model,
            mode=complexity or "suggestion",
            is_suggested=True,
        )
        return h.insert()

    def accept_suggestion(self) -> Hypothesis:
        """Accept: flip is_suggested, return self for further processing."""
        self.is_suggested = False
        self.save()
        return self

    def dismiss_suggestion(self) -> None:
        """Dismiss: delete the suggested hypothesis."""
        self.delete()

    @classmethod
    def suggested(cls) -> list[Hypothesis]:
        """List suggested (not yet accepted) hypotheses."""
        return cls.all(where="is_suggested = TRUE", order_by="created_at DESC")

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
        mode: str = "hypothesis",
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
            mode=mode,
        )
        return h.insert()

    # ------------------------------------------------------------------
    # Recipe / Result accessors -- deserialize JSON columns lazily.
    # ------------------------------------------------------------------

    def recipe(self) -> Recipe:
        """Reconstruct the :class:`Recipe` from ``recipe_json``."""
        from shenas_analyses.core.analytics import Recipe

        return Recipe.model_validate_json(self.recipe_json)

    def result(self) -> Result | None:
        """Reconstruct the most recent :class:`Result` from ``result_json``,
        or ``None`` if the recipe hasn't been executed yet."""
        from pydantic import TypeAdapter
        from shenas_analyses.core.analytics.runner import Result

        raw = self.result_json
        if not raw:
            return None
        return TypeAdapter(Result).validate_json(raw)

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

        The actual class generation + materialization happens elsewhere.
        This is just the breadcrumb on the row.
        """
        self.promoted_to = qualified_metric_name
        return self.save()


# ----------------------------------------------------------------------
# Recipe / Result JSON serialization helpers
# ----------------------------------------------------------------------


def _serialize_recipe(recipe: Recipe) -> str:
    """Serialize a Recipe DAG to JSON."""
    return recipe.model_dump_json()


def _serialize_result(result: Result) -> str:
    """Serialize a Result tagged union to JSON."""
    return result.model_dump_json()


def _extract_input_tables(recipe: Recipe) -> list[str]:
    """Return the qualified names of every SourceRef in the recipe.

    Persisted in the ``inputs`` column so the future "what depends on
    table X?" query is a simple LIKE -- no need to deserialize the
    recipe JSON.
    """
    from shenas_analyses.core.analytics import SourceRef

    return [node.table for node in recipe.nodes.values() if isinstance(node, SourceRef)]
