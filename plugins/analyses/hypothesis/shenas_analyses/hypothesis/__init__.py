"""Hypothesis testing analysis plugin.

Translates a user's natural-language question into a Recipe DAG that
explores correlations, trends, and comparisons across the personal-data
warehouse. The LLM picks from the five built-in operations: ``lag``,
``rolling``, ``resample``, ``join_as_of``, ``correlate``.
"""

from __future__ import annotations

from typing import ClassVar

from shenas_analyses.core import Analysis, AnalysisMode, Operation

from shenas_plugins.core.analytics.operations import (
    Correlate,
    JoinAsOf,
    Lag,
    Resample,
    Rolling,
)


class HypothesisMode(AnalysisMode):
    """Hypothesis testing: explore correlations and trends."""

    name: ClassVar[str] = "hypothesis"
    display_name: ClassVar[str] = "Hypothesis Testing"
    description: ClassVar[str] = (
        "Explore correlations, trends, and comparisons across your data. "
        "Ask questions like 'does caffeine affect my sleep?' or "
        "'what is the trend in my resting heart rate?'"
    )
    operations: ClassVar[tuple[type[Operation], ...]] = (
        Lag,
        Rolling,
        Resample,
        JoinAsOf,
        Correlate,
    )

    def _persona(self) -> str:
        return (
            "You are a data analyst translating natural-language questions about a "
            "personal-data warehouse into structured Recipe DAGs."
        )


class HypothesisAnalysis(Analysis):
    """Hypothesis testing analysis plugin."""

    name: ClassVar[str] = "hypothesis"
    display_name: ClassVar[str] = "Hypothesis Testing"
    description: ClassVar[str] = "Explore correlations, trends, and comparisons across your data."
    mode_cls: ClassVar[type[AnalysisMode]] = HypothesisMode
