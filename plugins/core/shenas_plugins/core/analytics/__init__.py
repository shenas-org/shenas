"""Analytics primitives for LLM-driven hypothesis testing.

A small, curated layer between an LLM and the underlying DuckDB data:

- :class:`RecipeNode` -- a typed wrapper around an Ibis expression that
  carries the originating table's "kind" forward through the pipeline.
  Operations consume and produce ``RecipeNode``s.

- :mod:`operations` -- the curated set of operations the LLM is allowed
  to compose. Each operation validates its inputs against the carrier's
  kind, lowers to an :class:`ibis.Expr`, and predicts its output kind.
  The LLM never writes SQL or raw Ibis; it picks operations and
  parameters from this fixed vocabulary.

This module is intentionally narrow. New operations are added by humans,
not by the LLM. The vocabulary is small enough to fit in one Anthropic
system prompt and large enough to express the most common hypothesis
shapes (lag this, window that, join AS-OF, correlate the two).
"""

from shenas_plugins.core.analytics.node import RecipeNode
from shenas_plugins.core.analytics.operations import (
    OPERATIONS,
    Correlate,
    JoinAsOf,
    Lag,
    Operation,
    OperationError,
    Resample,
    Rolling,
)
from shenas_plugins.core.analytics.recipe import OpCall, Recipe, RecipeError, SourceRef

__all__ = [
    "OPERATIONS",
    "Correlate",
    "JoinAsOf",
    "Lag",
    "OpCall",
    "Operation",
    "OperationError",
    "Recipe",
    "RecipeError",
    "RecipeNode",
    "Resample",
    "Rolling",
    "SourceRef",
]
