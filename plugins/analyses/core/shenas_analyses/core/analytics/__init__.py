"""Analytics primitives for LLM-driven analysis.

A small, curated layer between an LLM and the underlying DuckDB data:

- :class:`RecipeNode` -- a typed wrapper around an Ibis expression that
  carries the originating table's "kind" forward through the pipeline.
  Operations consume and produce ``RecipeNode``s.

- :mod:`operations` -- the curated set of operations the LLM is allowed
  to compose. Each operation validates its inputs against the carrier's
  kind, lowers to an :class:`ibis.Expr`, and predicts its output kind.
  The LLM never writes SQL or raw Ibis; it picks operations and
  parameters from this fixed vocabulary.

- :class:`AnalysisMode` -- the extension point for different analysis
  strategies. Each mode owns its operation subset, system prompt, and
  tool definition. Modes are registered by analysis plugins via entry
  points.

This module is intentionally narrow. New operations are added by humans,
not by the LLM. The vocabulary is small enough to fit in one Anthropic
system prompt and large enough to express the most common analysis
shapes (lag this, window that, join AS-OF, correlate the two).
"""

from shenas_analyses.core.analytics.llm import (
    ask_for_interpretation,
    ask_for_recipe,
    ask_for_recipe_with_retry,
    build_system_prompt,
    build_user_prompt,
    operation_param_schema,
)
from shenas_analyses.core.analytics.mode import (
    AnalysisMode,
    get_mode,
    list_modes,
    register_mode,
)
from shenas_analyses.core.analytics.node import RecipeNode
from shenas_analyses.core.analytics.operations import (
    Correlate,
    JoinAsOf,
    Lag,
    Operation,
    OperationError,
    Resample,
    Rolling,
    get_operations,
    register_operation,
)
from shenas_analyses.core.analytics.recipe import OpCall, Recipe, RecipeError, SourceRef
from shenas_analyses.core.analytics.runner import (
    ErrorResult,
    Result,
    ScalarResult,
    TableResult,
    run_recipe,
)

from app.llm import FakeProvider, LLMProvider

__all__ = [
    "AnalysisMode",
    "Correlate",
    "ErrorResult",
    "FakeProvider",
    "JoinAsOf",
    "LLMProvider",
    "Lag",
    "OpCall",
    "Operation",
    "OperationError",
    "Recipe",
    "RecipeError",
    "RecipeNode",
    "Resample",
    "Result",
    "Rolling",
    "ScalarResult",
    "SourceRef",
    "TableResult",
    "ask_for_interpretation",
    "ask_for_recipe",
    "ask_for_recipe_with_retry",
    "build_system_prompt",
    "build_user_prompt",
    "get_mode",
    "get_operations",
    "list_modes",
    "operation_param_schema",
    "register_mode",
    "register_operation",
    "run_recipe",
]
