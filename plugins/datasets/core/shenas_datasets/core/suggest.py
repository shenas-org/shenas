"""LLM-driven dataset + transform suggestions.

Given a user's installed sources (with rich table metadata), asks an LLM
to suggest canonical metric tables and the SQL transforms that populate
them. This is plugin introspection -- "what datasets should exist given
these sources?" -- not data analysis.
"""

from __future__ import annotations

import json
from typing import Any

# ----------------------------------------------------------------------
# Tool schema
# ----------------------------------------------------------------------


def submit_dataset_suggestions_tool() -> dict[str, Any]:
    """Anthropic tool-use definition for dataset + transform suggestions."""
    return {
        "name": "submit_dataset_suggestions",
        "description": (
            "Submit suggested canonical metric tables and the SQL transforms that populate them from raw source tables."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "description": "List of suggested metric tables with their transforms.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Human-readable name, e.g. 'Daily Music Listening'.",
                            },
                            "description": {
                                "type": "string",
                                "description": "Why this metric table is useful.",
                            },
                            "table_name": {
                                "type": "string",
                                "description": "DuckDB table name in snake_case, e.g. 'daily_music'.",
                            },
                            "grain": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly", "event"],
                                "description": "Temporal grain of the metric table.",
                            },
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "db_type": {"type": "string"},
                                        "description": {"type": "string"},
                                        "unit": {"type": "string"},
                                        "nullable": {"type": "boolean"},
                                    },
                                    "required": ["name", "db_type", "description"],
                                },
                            },
                            "primary_key": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "transforms": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "source_schema": {"type": "string"},
                                        "source_table": {"type": "string"},
                                        "source_plugin": {"type": "string"},
                                        "description": {"type": "string"},
                                        "sql": {"type": "string"},
                                    },
                                    "required": [
                                        "source_schema",
                                        "source_table",
                                        "source_plugin",
                                        "sql",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "title",
                            "description",
                            "table_name",
                            "grain",
                            "columns",
                            "primary_key",
                            "transforms",
                        ],
                    },
                },
            },
            "required": ["suggestions"],
        },
    }


# ----------------------------------------------------------------------
# Prompt assembly
# ----------------------------------------------------------------------


def build_dataset_system_prompt() -> str:
    """System prompt explaining metric conventions to the LLM."""
    return (
        "You are a data architect for a personal data warehouse backed by DuckDB.\n"
        "You see raw source tables (synced from external APIs) and existing canonical\n"
        "metric tables. Suggest NEW canonical metric tables and SQL transforms.\n\n"
        "Conventions:\n"
        "- Metric tables live in the `metrics` schema.\n"
        "- Daily metrics: PK = (date, source), date is DATE, source is VARCHAR.\n"
        "- Weekly metrics: PK = (week, source).\n"
        "- Monthly metrics: PK = (month, source), month is VARCHAR 'YYYY-MM'.\n"
        "- Event metrics: PK = (source, source_id) or (id, source).\n"
        "- The `source` column always identifies the data source (e.g. 'garmin', 'spotify').\n"
        "- Column names: snake_case with unit suffixes (distance_m, weight_kg, duration_s).\n"
        "- Units: SI -- m, s, kg, W, kJ, bpm, degC, kcal, percent, bytes, min, rpm.\n"
        "- Transforms: idempotent SQL. System runs DELETE WHERE source=<plugin> then INSERT.\n"
        "- Transform SQL: SELECT with aliases matching target columns. Include source literal.\n"
        "- Do NOT suggest metrics that duplicate existing ones.\n"
        "- Each suggestion should be independently useful.\n\n"
        "Respond by calling `submit_dataset_suggestions`."
    )


def build_dataset_user_prompt(
    source_catalog: list[dict[str, Any]],
    existing_metrics: list[dict[str, Any]],
) -> str:
    """Per-request prompt: source tables + existing metrics so LLM avoids duplicates."""
    sources_str = json.dumps(source_catalog, indent=2, default=str)
    metrics_str = json.dumps(existing_metrics, indent=2, default=str)
    return (
        f"## Raw source tables\n\n{sources_str}\n\n"
        f"## Existing metric tables (do NOT duplicate these)\n\n{metrics_str}\n\n"
        "Suggest new canonical metric tables and SQL transforms that would add value.\n"
        "Respond by calling `submit_dataset_suggestions`."
    )


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------


def validate_dataset_payload(payload: dict[str, Any]) -> None:
    """Validate the structural shape of the LLM's suggestion payload.

    Raises ``ValueError`` on invalid payloads so the retry loop in
    ``ask_for_recipe_with_retry`` can re-prompt.
    """
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        msg = "payload must contain a non-empty 'suggestions' array"
        raise ValueError(msg)
    for i, s in enumerate(suggestions):
        for field in ("title", "table_name", "grain", "columns", "primary_key", "transforms"):
            if field not in s:
                msg = f"suggestion[{i}] missing required field '{field}'"
                raise ValueError(msg)
        if s["grain"] not in ("daily", "weekly", "monthly", "event"):
            msg = f"suggestion[{i}] has invalid grain '{s['grain']}'"
            raise ValueError(msg)
        if not s["columns"]:
            msg = f"suggestion[{i}] has empty columns"
            raise ValueError(msg)
        if not s["primary_key"]:
            msg = f"suggestion[{i}] has empty primary_key"
            raise ValueError(msg)
        col_names = {c["name"] for c in s["columns"]}
        for pk in s["primary_key"]:
            if pk not in col_names:
                msg = f"suggestion[{i}] PK column '{pk}' not in columns"
                raise ValueError(msg)


# ----------------------------------------------------------------------
# High-level entry point
# ----------------------------------------------------------------------


def ask_for_dataset_suggestions(
    provider: Any,
    source_catalog: list[dict[str, Any]],
    existing_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask the LLM for dataset + transform suggestions.

    Returns the raw tool-input dict. Caller is responsible for
    persisting the suggestions.
    """
    system = build_dataset_system_prompt()
    user = build_dataset_user_prompt(source_catalog, existing_metrics)
    tools = [submit_dataset_suggestions_tool()]
    return provider.ask(system=system, user=user, tools=tools)
