"""Analysis suggestion plugin.

Suggests interesting analyses, correlations, and hypotheses the user
could explore given their canonical metric tables. Unlike the hypothesis
mode which translates questions into Recipe DAGs, this mode generates
the questions themselves.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from shenas_analyses.core import Analysis, AnalysisMode, Operation


class SuggestionMode(AnalysisMode):
    """Suggest interesting analyses given available metric tables."""

    name: ClassVar[str] = "suggestion"
    display_name: ClassVar[str] = "Analysis Suggestions"
    description: ClassVar[str] = (
        "Suggest interesting analyses, correlations, and hypotheses to explore "
        "based on the metric tables available in your data warehouse."
    )
    operations: ClassVar[tuple[type[Operation], ...]] = ()

    def _persona(self) -> str:
        return (
            "You are a data analyst exploring a personal data warehouse. "
            "Suggest interesting analyses, correlations, and hypotheses "
            "the user could explore."
        )

    def _constraints(self) -> str:
        return (
            "You MUST respond by calling the `submit_analysis_suggestions` tool.\n\n"
            "Focus on:\n"
            "- Cross-dataset correlations (e.g. sleep vs. exercise performance, "
            "spending patterns vs. mood)\n"
            "- Temporal patterns (weekly cycles, seasonal trends, day-of-week effects)\n"
            "- Anomaly detection (unusual values, trend breaks, outliers)\n"
            "- Goal tracking (fitness targets, budget adherence, habit streaks)\n"
            "- Actionable insights the user can act on\n\n"
            "Each suggestion should be a clear, natural-language question that can "
            "be answered by querying the available metric tables. Be specific -- "
            "reference actual table and column names from the catalog."
        )

    def _operation_vocabulary(self) -> str:
        # This mode doesn't use recipe operations.
        return ""

    def _recipe_format(self) -> str:
        # This mode doesn't produce recipes.
        return ""

    def build_system_prompt(self) -> str:
        return self._persona() + "\n\n" + self._constraints()

    def submit_tool(self) -> dict[str, Any]:
        return {
            "name": "submit_analysis_suggestions",
            "description": "Submit suggested analysis questions for the user to explore.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "description": "List of suggested analysis questions.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "A clear natural-language question.",
                                },
                                "rationale": {
                                    "type": "string",
                                    "description": "Why this analysis is interesting or useful.",
                                },
                                "datasets_involved": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Qualified metric table names (e.g. 'metrics.daily_hrv').",
                                },
                                "complexity": {
                                    "type": "string",
                                    "enum": ["simple", "moderate", "complex"],
                                    "description": "How complex the analysis would be.",
                                },
                            },
                            "required": ["question", "rationale", "datasets_involved"],
                        },
                    },
                },
                "required": ["suggestions"],
            },
        }


def build_analysis_user_prompt(metrics_catalog: list[dict[str, Any]]) -> str:
    """Per-request prompt: metric tables available for analysis."""
    catalog_str = json.dumps(metrics_catalog, indent=2, default=str)
    return (
        f"## Available metric tables\n\n{catalog_str}\n\n"
        "Suggest interesting analyses the user could explore with these tables.\n"
        "Respond by calling `submit_analysis_suggestions`."
    )


def validate_analysis_payload(payload: dict[str, Any]) -> None:
    """Validate the structural shape of the analysis suggestion payload."""
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        msg = "payload must contain a non-empty 'suggestions' array"
        raise ValueError(msg)
    for i, s in enumerate(suggestions):
        if "question" not in s:
            msg = f"suggestion[{i}] missing required field 'question'"
            raise ValueError(msg)
        if "rationale" not in s:
            msg = f"suggestion[{i}] missing required field 'rationale'"
            raise ValueError(msg)
        if "datasets_involved" not in s:
            msg = f"suggestion[{i}] missing required field 'datasets_involved'"
            raise ValueError(msg)


def ask_for_analysis_suggestions(
    provider: Any,
    metrics_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask the LLM for analysis suggestions.

    Returns the raw tool-input dict. Caller persists as Hypothesis rows.
    """
    mode = SuggestionMode()
    system = mode.build_system_prompt()
    user = build_analysis_user_prompt(metrics_catalog)
    tools = [mode.submit_tool()]
    return provider.ask(system=system, user=user, tools=tools)


class SuggestionAnalysis(Analysis):
    """Analysis suggestion plugin."""

    name: ClassVar[str] = "suggestion"
    display_name: ClassVar[str] = "Analysis Suggestions"
    description: ClassVar[str] = "Suggest interesting analyses based on available data."
    mode_cls: ClassVar[type[AnalysisMode]] = SuggestionMode
