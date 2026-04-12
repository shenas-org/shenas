"""Tests for the LLM integration module."""

from __future__ import annotations

import json
from typing import Any

import pytest
from shenas_analyses.core.analytics import (
    FakeProvider,
    ask_for_recipe,
    build_system_prompt,
    build_user_prompt,
    get_mode,
    get_operations,
    operation_param_schema,
)


@pytest.fixture(autouse=True)
def _ensure_hypothesis_mode():
    """Import the hypothesis plugin so the default mode is registered."""
    import shenas_analyses.hypothesis  # noqa: F401


def test_operation_param_schema_lag():
    from shenas_analyses.core.analytics.operations import Lag

    schema = operation_param_schema(Lag)
    assert schema["type"] == "object"
    props = schema["properties"]
    assert "column" in props
    assert "n" in props
    assert props["n"]["type"] == "integer"
    # `column` has no default, so it's required
    assert "column" in schema["required"]


def test_submit_tool_shape():
    mode = get_mode("hypothesis")
    tool = mode.submit_tool()
    assert tool["name"] == "submit_recipe"
    assert "input_schema" in tool
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"plan", "nodes", "final"}


def test_system_prompt_lists_every_operation():
    mode = get_mode("hypothesis")
    prompt = build_system_prompt(mode)
    for op_cls in get_operations().values():
        assert op_cls.name in prompt


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
    mode = get_mode("hypothesis")
    provider = FakeProvider(canned)
    result = ask_for_recipe(provider, "does coffee affect mood?", {}, mode=mode)
    assert result == canned
    assert len(provider.calls) == 1
    system, user = provider.calls[0]
    assert "submit_recipe" in system
    assert "does coffee affect mood?" in user


def test_anthropic_provider_raises_without_api_key(monkeypatch):
    from shenas_analyses.core.analytics import AnthropicProvider

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
    from shenas_analyses.core.analytics import ask_for_recipe_with_retry

    payloads = iter(
        [
            {"plan": "first", "nodes": {}, "final": ""},  # validate raises
            {"plan": "second", "nodes": {"a": {"type": "source", "table": "x"}}, "final": "a"},  # passes
        ]
    )

    class _SeqProvider:
        name = "seq@v0"
        last_input_tokens = 0
        last_output_tokens = 0

        def __init__(self):
            self.calls: list[str] = []

        def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
            self.calls.append(user)
            return next(payloads)

    def _validate(p):
        if not p.get("nodes"):
            raise ValueError("recipe has no nodes")

    mode = get_mode("hypothesis")
    provider = _SeqProvider()
    payload, errors = ask_for_recipe_with_retry(provider, "q", {}, mode=mode, validate=_validate, max_attempts=2)  # ty: ignore[invalid-argument-type]
    assert payload["plan"] == "second"
    assert len(errors) == 1
    # Second user prompt includes the error from attempt 1
    assert "no nodes" in provider.calls[1]


def test_iteration_loop_gives_up_after_max_attempts():
    from shenas_analyses.core.analytics import ask_for_recipe_with_retry

    class _AlwaysBad:
        name = "bad@v0"
        last_input_tokens = 0
        last_output_tokens = 0

        def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
            return {"plan": "x", "nodes": {}, "final": ""}

    def _validate(_):
        raise ValueError("always invalid")

    mode = get_mode("hypothesis")
    payload, errors = ask_for_recipe_with_retry(_AlwaysBad(), "q", {}, mode=mode, validate=_validate, max_attempts=2)  # ty: ignore[invalid-argument-type]
    assert len(errors) == 2
    assert payload["plan"] == "x"


def test_operation_vocabulary_is_valid_json_in_prompt():
    """Each operation's params schema embedded in the prompt is valid JSON."""
    mode = get_mode("hypothesis")
    prompt = build_system_prompt(mode)
    # Each operation block has a `params: {...}` line.
    for line in prompt.splitlines():
        if line.startswith("params: "):
            json.loads(line.removeprefix("params: "))  # raises if malformed


def test_dynamic_operation_registry():
    """register_operation makes new ops visible to get_operations."""
    from dataclasses import dataclass
    from typing import ClassVar

    from shenas_analyses.core.analytics.operations import (
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
