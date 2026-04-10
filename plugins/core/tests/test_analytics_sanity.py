"""Tests for sanity rules."""

from __future__ import annotations

import math

from shenas_plugins.core.analytics import ErrorResult, ScalarResult, TableResult
from shenas_plugins.core.analytics.sanity import sanity_check


def test_clean_scalar_no_warnings():
    r = ScalarResult(value=0.42, column="rate")
    assert sanity_check(r) == []


def test_null_scalar_warns():
    r = ScalarResult(value=None, column="x")
    assert any("null" in w for w in sanity_check(r))


def test_nan_scalar_warns():
    r = ScalarResult(value=float("nan"), column="x")
    assert any("NaN" in w for w in sanity_check(r))


def test_correlation_out_of_range_warns():
    r = ScalarResult(value=1.5, column="caffeine_mood_corr")
    assert any("outside" in w for w in sanity_check(r))


def test_empty_table_warns():
    r = TableResult(rows=[], columns=["a"], row_count=0)
    assert any("empty" in w for w in sanity_check(r))


def test_few_rows_warns():
    r = TableResult(
        rows=[{"a": 1}, {"a": 2}],
        columns=["a"],
        row_count=2,
    )
    warnings = sanity_check(r)
    assert any("too few" in w for w in warnings)


def test_all_null_column_warns():
    r = TableResult(
        rows=[{"a": 1, "b": None}, {"a": 2, "b": None}, {"a": 3, "b": None}, {"a": 4, "b": None}, {"a": 5, "b": None}],
        columns=["a", "b"],
        row_count=5,
    )
    warnings = sanity_check(r)
    assert any("`b`" in w and "null" in w for w in warnings)


def test_zero_variance_column_warns():
    r = TableResult(
        rows=[{"a": 7} for _ in range(15)],
        columns=["a"],
        row_count=15,
    )
    warnings = sanity_check(r)
    assert any("zero variance" in w for w in warnings)


def test_error_result_no_warnings():
    """Sanity rules don't apply to ErrorResults."""
    r = ErrorResult(message="boom", kind="execution")
    assert sanity_check(r) == []


def test_model_dump_includes_warnings():
    """Result.model_dump() flows warnings out for GraphQL consumers."""
    r = ScalarResult(value=float("nan"), column="x").with_warnings()
    d = r.model_dump()
    assert "warnings" in d
    assert any("NaN" in w for w in d["warnings"])
    # Sanity check imports at runtime
    assert not math.isnan(0)  # silence unused import
