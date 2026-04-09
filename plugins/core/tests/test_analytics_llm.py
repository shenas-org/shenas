"""Tests for the LLM integration module (PR 2.3)."""

from __future__ import annotations

import json

from shenas_plugins.core.analytics import (
    OPERATIONS,
    FakeProvider,
    ask_for_recipe,
    build_system_prompt,
    build_user_prompt,
    operation_param_schema,
    submit_recipe_tool,
)


def test_operation_param_schema_lag():
    from shenas_plugins.core.analytics.operations import Lag

    schema = operation_param_schema(Lag)
    assert schema["type"] == "object"
    props = schema["properties"]
    assert "column" in props
    assert "n" in props
    assert props["n"]["type"] == "integer"
    # `column` has no default, so it's required
    assert "column" in schema["required"]


def test_submit_recipe_tool_shape():
    tool = submit_recipe_tool()
    assert tool["name"] == "submit_recipe"
    assert "input_schema" in tool
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"plan", "nodes", "final"}


def test_system_prompt_lists_every_operation():
    prompt = build_system_prompt()
    for op in OPERATIONS:
        assert op.name in prompt


def test_user_prompt_includes_question_and_catalog():
    catalog = {
        "metrics.daily_intake": {"table": "daily_intake", "schema": "metrics", "kind": "daily_metric"},
    }
    prompt = build_user_prompt("does coffee affect mood?", catalog)
    assert "does coffee affect mood?" in prompt
    assert "daily_intake" in prompt
    assert "submit_recipe" in prompt


def test_ask_for_recipe_round_trip_via_fake_provider():
    canned = {
        "plan": "Look at correlation between caffeine and mood.",
        "nodes": {
            "a": {"type": "source", "table": "metrics.daily_intake"},
            "b": {"type": "source", "table": "metrics.daily_outcomes"},
            "j": {"type": "op", "op_name": "join_as_of", "params": {"on": "date"}, "inputs": ["a", "b"]},
            "r": {
                "type": "op",
                "op_name": "correlate",
                "params": {"x": "caffeine_mg", "y": "mood"},
                "inputs": ["j"],
            },
        },
        "final": "r",
    }
    provider = FakeProvider(canned)
    result = ask_for_recipe(provider, "does coffee affect mood?", {})
    assert result == canned
    assert len(provider.calls) == 1
    system, user = provider.calls[0]
    assert "submit_recipe" in system
    assert "does coffee affect mood?" in user


def test_anthropic_provider_raises_without_api_key(monkeypatch):
    from shenas_plugins.core.analytics import AnthropicProvider

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicProvider()
    try:
        p.ask(system="s", user="u", tools=[])
    except RuntimeError as exc:
        msg = str(exc)
        assert "ANTHROPIC_API_KEY" in msg or "anthropic" in msg.lower()
        return
    raise AssertionError("expected RuntimeError")


def test_operation_vocabulary_is_valid_json_in_prompt():
    """Each operation's params schema embedded in the prompt is valid JSON."""
    prompt = build_system_prompt()
    # Each operation block has a `params: {...}` line.
    for line in prompt.splitlines():
        if line.startswith("params: "):
            json.loads(line.removeprefix("params: "))  # raises if malformed
