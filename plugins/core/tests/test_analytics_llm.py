"""Tests for the LLM integration module."""

from __future__ import annotations

import json

import pytest

from shenas_plugins.core.analytics import (
    OPERATIONS,
    FakeProvider,
    ask_for_recipe,
    build_system_prompt,
    build_user_prompt,
    operation_param_schema,
    submit_recipe_tool,
)


@pytest.fixture(autouse=True)
def _ensure_hypothesis_mode():
    """Import the hypothesis plugin so the default mode is registered."""
    import shenas_analyses.hypothesis  # noqa: F401


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


def test_iteration_loop_retries_once_on_validation_error():
    """The retry loop sends the validation error back to the LLM and accepts the second attempt."""
    from shenas_plugins.core.analytics import ask_for_recipe_with_retry

    payloads = iter(
        [
            {"plan": "first", "nodes": {}, "final": ""},  # validate raises
            {"plan": "second", "nodes": {"a": {"type": "source", "table": "x"}}, "final": "a"},  # passes
        ]
    )

    class _SeqProvider:
        name = "seq@v0"

        def __init__(self):
            self.calls = []

        def ask(self, *, system, user, tools):
            self.calls.append(user)
            return next(payloads)

    def _validate(p):
        if not p.get("nodes"):
            raise ValueError("recipe has no nodes")

    provider = _SeqProvider()
    payload, errors = ask_for_recipe_with_retry(provider, "q", {}, validate=_validate, max_attempts=2)
    assert payload["plan"] == "second"
    assert len(errors) == 1
    # Second user prompt includes the error from attempt 1
    assert "no nodes" in provider.calls[1]


def test_iteration_loop_gives_up_after_max_attempts():
    from shenas_plugins.core.analytics import ask_for_recipe_with_retry

    class _AlwaysBad:
        name = "bad@v0"

        def ask(self, *, system, user, tools):
            return {"plan": "x", "nodes": {}, "final": ""}

    def _validate(_):
        raise ValueError("always invalid")

    payload, errors = ask_for_recipe_with_retry(_AlwaysBad(), "q", {}, validate=_validate, max_attempts=2)
    assert len(errors) == 2
    assert payload["plan"] == "x"


def test_operation_vocabulary_is_valid_json_in_prompt():
    """Each operation's params schema embedded in the prompt is valid JSON."""
    prompt = build_system_prompt()
    # Each operation block has a `params: {...}` line.
    for line in prompt.splitlines():
        if line.startswith("params: "):
            json.loads(line.removeprefix("params: "))  # raises if malformed


def test_ask_for_recipe_with_mode():
    """ask_for_recipe accepts an explicit mode and uses its prompt/tool."""
    from shenas_plugins.core.analytics import FakeProvider, ask_for_recipe, get_mode

    mode = get_mode("hypothesis")
    canned = {
        "plan": "test plan",
        "nodes": {"a": {"type": "source", "table": "metrics.x"}},
        "final": "a",
    }
    provider = FakeProvider(canned)
    result = ask_for_recipe(provider, "test question", {}, mode=mode)
    assert result == canned
    # The system prompt used should be the mode's prompt
    system, _ = provider.calls[0]
    assert "lag" in system
    assert "correlate" in system


def test_ask_for_recipe_with_retry_passes_mode():
    """ask_for_recipe_with_retry forwards the mode to the provider."""
    from shenas_plugins.core.analytics import FakeProvider, ask_for_recipe_with_retry, get_mode

    mode = get_mode("hypothesis")
    canned = {
        "plan": "p",
        "nodes": {"a": {"type": "source", "table": "x"}},
        "final": "a",
    }
    provider = FakeProvider(canned)
    payload, errors = ask_for_recipe_with_retry(provider, "q", {}, mode=mode)
    assert payload == canned
    assert errors == []


def test_build_system_prompt_with_mode():
    """build_system_prompt delegates to the mode when provided."""
    from shenas_plugins.core.analytics import build_system_prompt, get_mode

    mode = get_mode("hypothesis")
    prompt = build_system_prompt(mode=mode)
    for op in mode.operations:
        assert op.name in prompt


def test_dynamic_operation_registry():
    """register_operation makes new ops visible to get_operations."""
    from dataclasses import dataclass
    from typing import ClassVar

    from shenas_plugins.core.analytics.operations import (
        _OPERATION_REGISTRY,
        Operation,
        get_operations,
        register_operation,
    )

    @dataclass(frozen=True)
    class _FakeOp(Operation):
        name: ClassVar[str] = "_test_fake_op"
        arity: ClassVar[int] = 1

    register_operation(_FakeOp)
    try:
        assert "_test_fake_op" in get_operations()
        assert get_operations()["_test_fake_op"] is _FakeOp
    finally:
        _OPERATION_REGISTRY.pop("_test_fake_op", None)
