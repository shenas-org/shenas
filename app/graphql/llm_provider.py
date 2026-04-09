"""LLM provider lookup for the GraphQL layer.

Indirection point so tests can swap in a fake provider via
``patch("app.graphql.llm_provider.get_llm_provider")``. Production
returns an :class:`AnthropicProvider`; the model can be overridden
via the ``SHENAS_LLM_MODEL`` env var.
"""

from __future__ import annotations

import os

from shenas_plugins.core.analytics import AnthropicProvider, LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider for hypothesis-driven analysis."""
    model = os.environ.get("SHENAS_LLM_MODEL", "claude-sonnet-4-6")
    return AnthropicProvider(model=model)
