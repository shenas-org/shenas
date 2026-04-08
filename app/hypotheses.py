"""Hypothesis records: persistent storage for LLM-driven analyses.

A :class:`HypothesisRecord` is the durable artifact of an LLM-authored
investigation: the user's natural-language question, the LLM's plan,
the recipe DAG it constructed, the inputs it referenced, the result
it observed, and the LLM's interpretation. One row per hypothesis,
stored in ``shenas_system.hypotheses`` (analogous to
``shenas_system.transforms``).

Recipes and results are JSON-serialized into ``recipe_json`` and
``result_json`` columns. The recipe is reconstructed via
:meth:`Recipe.compile` on demand; the result is cached but **not** the
source of truth -- the recipe is. Re-opening a hypothesis can either
read the cached result or replay the recipe against current data.

Promotion is the bridge from a hypothesis to a canonical metric table:
when the user explicitly says "save this analysis as a permanent
metric," the recipe gets converted into a ``MetricTable`` subclass and
the hypothesis row's ``promoted_to`` column captures the qualified
name of the new metric. **Promotion is the only path that creates
canonical state**; until promotion, every analytical transformation
is transient.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.db import cursor
from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    from shenas_plugins.core.analytics import Recipe, Result


_COLS = "id, question, plan, recipe_json, inputs, result_json, interpretation, created_at, model, promoted_to"


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "question": row[1],
        "plan": row[2],
        "recipe_json": row[3],
        "inputs": row[4],
        "result_json": row[5],
        "interpretation": row[6],
        "created_at": str(row[7]) if row[7] else None,
        "model": row[8],
        "promoted_to": row[9],
    }


class HypothesisRecord:
    """One LLM-authored investigation, end to end.

    Stored as a row in ``shenas_system.hypotheses``. Wraps the row in a
    light read-only proxy plus a small set of staticmethods for CRUD.
    The :class:`Recipe` and :class:`Result` (de)serialization happen
    via JSON; both are JSON-friendly by construction (frozen
    dataclasses with primitive fields).
    """

    class _Table(Table):
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

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    # ------------------------------------------------------------------
    # Recipe / Result accessors -- deserialize JSON columns lazily.
    # ------------------------------------------------------------------

    def recipe(self) -> Recipe:
        """Reconstruct the :class:`Recipe` from ``recipe_json``."""
        from shenas_plugins.core.analytics import OpCall, Recipe, SourceRef

        payload = json.loads(self._data["recipe_json"])
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

        raw = self._data.get("result_json")
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
    # Queries
    # ------------------------------------------------------------------

    @staticmethod
    def all(*, limit: int | None = None) -> list[HypothesisRecord]:
        """List all hypotheses, most recent first."""
        with cursor() as cur:
            if limit is not None:
                rows = cur.execute(
                    f"SELECT {_COLS} FROM shenas_system.hypotheses ORDER BY created_at DESC LIMIT ?",
                    [limit],
                ).fetchall()
            else:
                rows = cur.execute(f"SELECT {_COLS} FROM shenas_system.hypotheses ORDER BY created_at DESC").fetchall()
        return [HypothesisRecord(_row_to_dict(r)) for r in rows]

    @staticmethod
    def find(hypothesis_id: int) -> HypothesisRecord | None:
        with cursor() as cur:
            row = cur.execute(f"SELECT {_COLS} FROM shenas_system.hypotheses WHERE id = ?", [hypothesis_id]).fetchone()
        return HypothesisRecord(_row_to_dict(row)) if row else None

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        question: str,
        recipe: Recipe,
        *,
        plan: str = "",
        model: str = "",
    ) -> HypothesisRecord:
        """Create a new hypothesis row from a question + a Recipe.

        The result and interpretation are blank initially -- call
        :meth:`attach_result` and :meth:`attach_interpretation` after
        running the recipe.
        """
        recipe_json = _serialize_recipe(recipe)
        inputs_csv = ",".join(sorted(_extract_input_tables(recipe)))
        with cursor() as cur:
            row = cur.execute(
                "INSERT INTO shenas_system.hypotheses "
                "(question, plan, recipe_json, inputs, model) "
                "VALUES (?, ?, ?, ?, ?) "
                f"RETURNING {_COLS}",
                [question, plan, recipe_json, inputs_csv, model],
            ).fetchone()
        if row is None:
            msg = "failed to insert hypothesis"
            raise RuntimeError(msg)
        return HypothesisRecord(_row_to_dict(row))

    @staticmethod
    def attach_result(hypothesis_id: int, result: Result) -> HypothesisRecord:
        """Attach a freshly-computed Result to an existing hypothesis."""
        result_json = _serialize_result(result)
        with cursor() as cur:
            row = cur.execute(
                f"UPDATE shenas_system.hypotheses SET result_json = ? WHERE id = ? RETURNING {_COLS}",
                [result_json, hypothesis_id],
            ).fetchone()
        if row is None:
            msg = f"hypothesis {hypothesis_id} not found"
            raise ValueError(msg)
        return HypothesisRecord(_row_to_dict(row))

    @staticmethod
    def attach_interpretation(hypothesis_id: int, interpretation: str) -> HypothesisRecord:
        """Attach the LLM's narrative interpretation."""
        with cursor() as cur:
            row = cur.execute(
                f"UPDATE shenas_system.hypotheses SET interpretation = ? WHERE id = ? RETURNING {_COLS}",
                [interpretation, hypothesis_id],
            ).fetchone()
        if row is None:
            msg = f"hypothesis {hypothesis_id} not found"
            raise ValueError(msg)
        return HypothesisRecord(_row_to_dict(row))

    @staticmethod
    def mark_promoted(hypothesis_id: int, qualified_metric_name: str) -> HypothesisRecord:
        """Record that this hypothesis was promoted to a canonical metric table.

        The actual class generation + materialization happens elsewhere
        (Phase 3, PR 3.1). This is just the breadcrumb on the row.
        """
        with cursor() as cur:
            row = cur.execute(
                f"UPDATE shenas_system.hypotheses SET promoted_to = ? WHERE id = ? RETURNING {_COLS}",
                [qualified_metric_name, hypothesis_id],
            ).fetchone()
        if row is None:
            msg = f"hypothesis {hypothesis_id} not found"
            raise ValueError(msg)
        return HypothesisRecord(_row_to_dict(row))

    @staticmethod
    def delete(hypothesis_id: int) -> None:
        """Delete a hypothesis row. Idempotent: no error if missing."""
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hypotheses WHERE id = ?", [hypothesis_id])


# ----------------------------------------------------------------------
# Recipe / Result JSON serialization helpers
# ----------------------------------------------------------------------


def _serialize_recipe(recipe: Recipe) -> str:
    """Serialize a Recipe DAG to JSON.

    Lives here rather than on Recipe so the analytics package stays
    free of "how to persist" concerns. Format mirrors what
    :meth:`HypothesisRecord.recipe` deserializes.
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
    """Serialize a Result tagged union to JSON.

    The Result dataclasses are already JSON-friendly (their ``type``
    field is the discriminator); this just turns them into a dict and
    dumps it.
    """
    from dataclasses import asdict

    payload = asdict(result)
    return json.dumps(payload)


def _extract_input_tables(recipe: Recipe) -> list[str]:
    """Return the qualified names of every SourceRef in the recipe.

    Persisted in the ``inputs`` column so the future "what depends on
    table X?" query is a simple LIKE -- no need to deserialize the
    recipe JSON.
    """
    from shenas_plugins.core.analytics import SourceRef

    return [node.table for node in recipe.nodes.values() if isinstance(node, SourceRef)]
