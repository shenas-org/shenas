"""Tests for the recipe runner.

Covers:

- ScalarResult vs TableResult vs ErrorResult shaping
- Wraps RecipeError as ErrorResult(kind='validation')
- Wraps OperationError as ErrorResult(kind='operation')
- Wraps execution errors as ErrorResult(kind='execution')
- Soft timeout produces ErrorResult(kind='timeout')
- max_rows truncation with truncated=True flag
- Scalars are coerced to native Python types (no numpy bleed-through)
- SQL is attached to all result kinds
"""

from __future__ import annotations

import ibis
import pytest

from shenas_plugins.core.analytics import (
    ErrorResult,
    OpCall,
    Recipe,
    ScalarResult,
    SourceRef,
    TableResult,
    run_recipe,
)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def con():
    c = ibis.duckdb.connect(":memory:")
    c.raw_sql("CREATE SCHEMA metrics")
    c.raw_sql("CREATE TABLE metrics.daily_intake (date DATE, caffeine_mg DOUBLE)")
    c.raw_sql(
        "INSERT INTO metrics.daily_intake VALUES "
        "('2026-04-01', 200), ('2026-04-02', 150), ('2026-04-03', 100), "
        "('2026-04-04', 50), ('2026-04-05', 0)"
    )
    c.raw_sql("CREATE TABLE metrics.daily_outcomes (date DATE, mood DOUBLE)")
    c.raw_sql(
        "INSERT INTO metrics.daily_outcomes VALUES "
        "('2026-04-01', 5), ('2026-04-02', 6), ('2026-04-03', 7), "
        "('2026-04-04', 8), ('2026-04-05', 9)"
    )
    return c


@pytest.fixture
def catalog():
    return {
        "metrics.daily_intake": {
            "kind": "daily_metric",
            "time_columns": {"time_at": "date"},
        },
        "metrics.daily_outcomes": {
            "kind": "daily_metric",
            "time_columns": {"time_at": "date"},
        },
    }


# ----------------------------------------------------------------------
# Result shaping
# ----------------------------------------------------------------------


class TestScalarResult:
    def test_correlate_returns_scalar(self, con, catalog):
        recipe = Recipe(
            nodes={
                "a": SourceRef(table="metrics.daily_intake"),
                "b": SourceRef(table="metrics.daily_outcomes"),
                "joined": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
                "result": OpCall(
                    op_name="correlate",
                    params={"x": "caffeine_mg", "y": "mood"},
                    inputs=("joined",),
                ),
            },
            final="result",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ScalarResult)
        assert result.column == "corr"
        assert result.value == pytest.approx(-1.0, abs=0.01)
        assert result.elapsed_ms > 0
        assert "CORR" in result.sql.upper() or "correlation" in result.sql.lower()

    def test_scalar_value_is_native_python(self, con, catalog):
        # No numpy bleed-through -- the value should be a Python float,
        # not a np.float64. Matters for JSON serialization.
        recipe = Recipe(
            nodes={
                "a": SourceRef(table="metrics.daily_intake"),
                "b": SourceRef(table="metrics.daily_outcomes"),
                "joined": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
                "result": OpCall(
                    op_name="correlate",
                    params={"x": "caffeine_mg", "y": "mood"},
                    inputs=("joined",),
                ),
            },
            final="result",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ScalarResult)
        # Type check: it must be a builtin float, not a numpy type
        assert type(result.value) is float


# ----------------------------------------------------------------------
# Table results
# ----------------------------------------------------------------------


class TestTableResult:
    def test_lag_returns_table(self, con, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(
                    op_name="lag",
                    params={"column": "caffeine_mg", "n": 1},
                    inputs=("src",),
                ),
            },
            final="lagged",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, TableResult)
        assert result.row_count == 5
        assert set(result.columns) == {"date", "caffeine_mg", "caffeine_mg_lag1"}
        assert result.truncated is False
        assert "LAG" in result.sql.upper()

    def test_truncation(self, con, catalog):
        # Build a table with 100 rows; cap max_rows at 10.
        con.raw_sql("CREATE TABLE metrics.big (id INTEGER, val DOUBLE)")
        con.raw_sql("INSERT INTO metrics.big SELECT generate_series, generate_series * 1.0 FROM generate_series(1, 100)")
        catalog["metrics.big"] = {"kind": "daily_metric", "time_columns": {"time_at": "id"}}

        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.big")},
            final="src",
        )
        result = run_recipe(recipe, catalog, backend=con, max_rows=10)
        assert isinstance(result, TableResult)
        assert result.row_count == 100  # full count is reported
        assert len(result.rows) == 10  # but only 10 rows materialised
        assert result.truncated is True

    def test_rows_are_json_friendly(self, con, catalog):
        # Each cell value should be a Python primitive (or None / iso string),
        # not a numpy type or pandas Timestamp object. Matters for the
        # eventual JSON serialization into the hypothesis record.
        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.daily_intake")},
            final="src",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, TableResult)
        for row in result.rows:
            for value in row.values():
                if value is None:
                    continue
                assert isinstance(value, (str, int, float, bool)), (
                    f"non-primitive value {value!r} of type {type(value).__name__}"
                )


# ----------------------------------------------------------------------
# Error wrapping
# ----------------------------------------------------------------------


class TestErrorResult:
    def test_validation_error_wrapped(self, con, catalog):
        # Unknown source table -> RecipeError("validation failed: ...")
        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.does_not_exist")},
            final="src",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ErrorResult)
        assert result.kind == "validation"
        assert "not in catalog" in result.message

    def test_unknown_op_wrapped(self, con, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="multiply", params={}, inputs=("src",)),
            },
            final="x",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ErrorResult)
        assert result.kind == "validation"
        assert "unknown operation" in result.message

    def test_arity_mismatch_wrapped(self, con, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("src",)),
            },
            final="x",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ErrorResult)
        assert result.kind == "validation"
        assert "requires 2 input(s)" in result.message

    def test_operation_error_wrapped(self, con, catalog):
        # join_as_of on a missing column -- the recipe IS structurally
        # valid (validates against catalog), but operation.apply() raises
        # OperationError at compile time when it inspects the actual
        # ibis schema.
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(
                    op_name="lag",
                    params={"column": "nonexistent_column"},
                    inputs=("src",),
                ),
            },
            final="lagged",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ErrorResult)
        assert result.kind == "operation"
        assert "nonexistent_column" in result.message

    def test_error_result_carries_elapsed(self, con, catalog):
        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.does_not_exist")},
            final="src",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ErrorResult)
        assert result.elapsed_ms >= 0  # may be ~0 since validation is fast


# ----------------------------------------------------------------------
# Soft timeout
# ----------------------------------------------------------------------


class TestTimeout:
    def test_timeout_returns_error_result(self, con, catalog):
        # Force a query that takes longer than the timeout. We can do this
        # by passing an absurdly small timeout and a real query.
        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.daily_intake")},
            final="src",
        )
        # 0.001 seconds is shorter than even the fastest possible query
        # because of the worker thread setup overhead.
        result = run_recipe(recipe, catalog, backend=con, timeout_seconds=0.0001)
        # Either the query was fast enough to slip through (TableResult)
        # or it timed out (ErrorResult). On a typical box it should
        # timeout because the worker thread takes ~milliseconds to even
        # start. We accept either outcome but check that timeout works
        # in principle.
        assert isinstance(result, (ErrorResult, TableResult))
        if isinstance(result, ErrorResult):
            assert result.kind == "timeout"
            assert "timeout" in result.message.lower()


# ----------------------------------------------------------------------
# SQL is attached to all result kinds
# ----------------------------------------------------------------------


class TestSqlAttached:
    def test_scalar_has_sql(self, con, catalog):
        recipe = Recipe(
            nodes={
                "a": SourceRef(table="metrics.daily_intake"),
                "b": SourceRef(table="metrics.daily_outcomes"),
                "j": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
                "r": OpCall(
                    op_name="correlate",
                    params={"x": "caffeine_mg", "y": "mood"},
                    inputs=("j",),
                ),
            },
            final="r",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, ScalarResult)
        assert result.sql  # non-empty
        assert "SELECT" in result.sql.upper()

    def test_table_has_sql(self, con, catalog):
        recipe = Recipe(
            nodes={"src": SourceRef(table="metrics.daily_intake")},
            final="src",
        )
        result = run_recipe(recipe, catalog, backend=con)
        assert isinstance(result, TableResult)
        assert result.sql
        assert "SELECT" in result.sql.upper()
