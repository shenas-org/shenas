"""Tests for the hypothesis analysis plugin."""

from __future__ import annotations


def test_import_registers_mode():
    """Importing the plugin auto-registers the hypothesis mode."""
    import shenas_analyses.hypothesis  # noqa: F401

    from shenas_plugins.core.analytics.mode import get_mode

    mode = get_mode("hypothesis")
    assert mode.name == "hypothesis"
    assert mode.display_name == "Hypothesis Testing"


def test_hypothesis_mode_has_five_operations():
    from shenas_analyses.hypothesis import HypothesisMode

    mode = HypothesisMode()
    op_names = {op.name for op in mode.operations}
    assert op_names == {"lag", "rolling", "resample", "join_as_of", "correlate"}


def test_hypothesis_mode_prompt_contains_operations():
    from shenas_analyses.hypothesis import HypothesisMode

    mode = HypothesisMode()
    prompt = mode.build_system_prompt()
    for op in mode.operations:
        assert op.name in prompt
    assert "submit_recipe" in prompt


def test_hypothesis_analysis_plugin_kind():
    from shenas_analyses.hypothesis import HypothesisAnalysis

    assert HypothesisAnalysis._kind == "analysis"
    assert HypothesisAnalysis.name == "hypothesis"
