"""Tests for the AnalysisMode abstraction and registry."""

from __future__ import annotations

from typing import ClassVar

import pytest
from shenas_analyses.core.analytics.mode import (
    MODE_REGISTRY,
    AnalysisMode,
    get_mode,
    list_modes,
    register_mode,
)
from shenas_analyses.core.analytics.operations import Correlate, Lag, Operation, Rolling


class _TestMode(AnalysisMode):
    name: ClassVar[str] = "_test_only"
    display_name: ClassVar[str] = "Test Mode"
    description: ClassVar[str] = "A mode used only in tests."
    operations: ClassVar[tuple[type[Operation], ...]] = (Lag, Rolling)


@pytest.fixture(autouse=True)
def _cleanup_registry():
    """Remove any test-only modes after each test."""
    yield
    MODE_REGISTRY.pop("_test_only", None)


def test_register_and_get():
    mode = _TestMode()
    register_mode(mode)
    assert get_mode("_test_only") is mode


def test_get_unknown_raises():
    with pytest.raises(KeyError, match="unknown analysis mode"):
        get_mode("nonexistent_mode_xyz")


def test_list_modes_includes_hypothesis():
    # hypothesis is registered by the shenas-analysis-hypothesis plugin
    import shenas_analyses.hypothesis  # noqa: F401

    modes = list_modes()
    names = [m["name"] for m in modes]
    assert "hypothesis" in names


def test_list_modes_includes_registered():
    register_mode(_TestMode())
    modes = list_modes()
    names = [m["name"] for m in modes]
    assert "_test_only" in names
    test_mode = next(m for m in modes if m["name"] == "_test_only")
    assert test_mode["display_name"] == "Test Mode"
    assert test_mode["description"] == "A mode used only in tests."


def test_hypothesis_mode_operations():
    import shenas_analyses.hypothesis  # noqa: F401

    mode = get_mode("hypothesis")
    op_names = {op.name for op in mode.operations}
    assert op_names == {"lag", "rolling", "resample", "join_as_of", "correlate"}


def test_build_system_prompt_includes_mode_operations():
    mode = _TestMode()
    prompt = mode.build_system_prompt()
    assert "lag" in prompt
    assert "rolling" in prompt
    # Operations NOT in this mode should not appear.
    assert "correlate" not in prompt


def test_submit_tool_default_shape():
    mode = _TestMode()
    tool = mode.submit_tool()
    assert tool["name"] == "submit_recipe"
    assert set(tool["input_schema"]["required"]) == {"plan", "nodes", "final"}


def test_custom_persona():
    class _CustomMode(AnalysisMode):
        name: ClassVar[str] = "_custom"
        operations: ClassVar[tuple[type[Operation], ...]] = (Correlate,)

        def _persona(self) -> str:
            return "You are a root-cause analyst."

    mode = _CustomMode()
    prompt = mode.build_system_prompt()
    assert "root-cause analyst" in prompt
    assert "correlate" in prompt


def test_sanity_rules_default():
    mode = _TestMode()
    rules = mode.sanity_rules()
    assert "scalar" in rules
    assert "table" in rules
