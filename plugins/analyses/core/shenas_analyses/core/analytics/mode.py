"""AnalysisMode -- the extension point for different LLM analysis strategies.

Each mode owns the pieces that vary across analysis styles:

- The curated **operation subset** the LLM is allowed to use.
- The **system prompt** that frames the LLM's task.
- The **tool definition** the LLM must call to submit its answer.
- Mode-specific **sanity rules** applied to results.

Everything else -- the Recipe DAG shape, Ibis compilation, DuckDB
execution, result persistence, the catalog -- is shared infrastructure
that modes compose, not override.

Modes are registered by name in ``MODE_REGISTRY``. The GraphQL mutation
resolves the user's ``mode`` string to a concrete ``AnalysisMode``
instance. New modes are added by subclassing ``AnalysisMode`` and
calling ``register_mode``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from shenas_analyses.core.analytics.operations import Operation


class AnalysisMode:
    """Base class for analysis modes.

    Subclasses set the ClassVars and optionally override methods to
    customize the LLM interaction. The base class provides sensible
    defaults so a minimal mode only needs ``name`` and ``operations``.
    """

    name: ClassVar[str]
    display_name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    operations: ClassVar[tuple[type[Operation], ...]] = ()

    # -- System prompt ---------------------------------------------------

    def build_system_prompt(self) -> str:
        """Assemble the full system prompt for this mode.

        The default implementation renders the operation vocabulary from
        ``self.operations`` and wraps it in a generic recipe-building
        frame. Subclasses override to add mode-specific framing.
        """
        return (
            self._persona()
            + "\n\n"
            + self._constraints()
            + "\n\n"
            + self._operation_vocabulary()
            + "\n\n"
            + self._recipe_format()
        )

    def _persona(self) -> str:
        """Opening sentence that tells the LLM what role it plays."""
        return (
            "You are a data analyst translating natural-language questions about a "
            "personal-data warehouse into structured Recipe DAGs."
        )

    def _constraints(self) -> str:
        """Hard guardrails the LLM must follow."""
        return (
            "You MUST respond by calling the `submit_recipe` tool. Use only the "
            "operations listed below; do not invent new ones. Do not write SQL."
        )

    def _operation_vocabulary(self) -> str:
        """Render the curated operation library as a prompt section."""
        from shenas_analyses.core.analytics.llm import operation_param_schema

        out: list[str] = ["## Operation vocabulary", ""]
        for op in self.operations:
            params = operation_param_schema(op)
            out.append(f"### `{op.name}` (arity {op.arity})")
            out.append((op.__doc__ or "").strip())
            out.append("")
            out.append(f"params: {json.dumps(params)}")
            if op.accepts:
                out.append(f"accepts kinds: {sorted(op.accepts)}")
            out.append("")
        return "\n".join(out)

    def _recipe_format(self) -> str:
        """Describe the recipe node shape the LLM must emit."""
        return (
            "Recipe nodes are either:\n"
            '- `{"type": "source", "table": "<schema>.<name>"}` for a raw input\n'
            '- `{"type": "op", "op_name": "<name>", "params": {...}, "inputs": [...]}` for an operation call\n'
            "The `inputs` array names other nodes by key. The `final` field names the node "
            "whose result is the answer."
        )

    # -- Tool definition -------------------------------------------------

    def submit_tool(self) -> dict[str, Any]:
        """Build the Anthropic tool-use definition for this mode.

        The default returns the standard ``submit_recipe`` tool. Modes
        that need extra top-level fields (e.g. ``horizon_days`` for
        forecasting) override this.
        """
        return {
            "name": "submit_recipe",
            "description": (
                "Submit a Recipe DAG that answers the user's question. Each node is "
                "either a SourceRef (`type: source`, `table: <qualified.name>`) or "
                "an OpCall (`type: op`, `op_name: <name>`, `params: {...}`, "
                "`inputs: [<node_name>...]`). The `final` field names the node "
                "whose result the user sees."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "One-paragraph natural-language plan for how this recipe answers the question.",
                    },
                    "nodes": {
                        "type": "object",
                        "description": "Map of node name -> node definition (source or op).",
                        "additionalProperties": True,
                    },
                    "final": {
                        "type": "string",
                        "description": "Name of the node whose result is the answer.",
                    },
                },
                "required": ["plan", "nodes", "final"],
            },
        }

    # -- Sanity rules ----------------------------------------------------

    def sanity_rules(self) -> dict[str, Any]:
        """Return mode-specific sanity rules.

        The default delegates to the shared rules in ``sanity.py``.
        Modes override to add checks specific to their analysis style.
        """
        from shenas_analyses.core.analytics.sanity import SANITY_RULES

        return dict(SANITY_RULES)


# -- Registry ------------------------------------------------------------

MODE_REGISTRY: dict[str, AnalysisMode] = {}


def register_mode(mode: AnalysisMode) -> None:
    """Register a mode instance by its ``name``."""
    MODE_REGISTRY[mode.name] = mode


def get_mode(name: str) -> AnalysisMode:
    """Look up a registered mode by name. Raises ``KeyError`` if unknown."""
    try:
        return MODE_REGISTRY[name]
    except KeyError:
        available = sorted(MODE_REGISTRY)
        msg = f"unknown analysis mode `{name}` (available: {available})"
        raise KeyError(msg) from None


def list_modes() -> list[dict[str, str]]:
    """Return metadata for all registered modes, sorted by name."""
    return [
        {
            "name": m.name,
            "display_name": m.display_name or m.name,
            "description": m.description,
        }
        for m in sorted(MODE_REGISTRY.values(), key=lambda m: m.name)
    ]
