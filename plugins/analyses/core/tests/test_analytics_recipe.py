"""Tests for the Recipe DAG + topological compiler.

End-to-end against a real in-memory DuckDB via Ibis. Covers:

- Linear chain recipe compiles to one chained CTE
- Two-branch correlation recipe (parallel CTEs joined at the end) --
  the smoke test for "we can express the most common hypothesis shape"
- Validation: missing source, missing input ref, undeclared node,
  unknown operation, arity mismatch, cycle detection
- Topological order is deterministic (matters for content-hash dedup)
- to_sql() round-trip
"""

from __future__ import annotations

import ibis
import pytest
from shenas_analyses.core.analytics import (
    Lag,
    OpCall,
    Recipe,
    RecipeError,
    SourceRef,
)

# ----------------------------------------------------------------------
# Fixtures: a tiny duckdb backend with two daily metric tables.
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
    """A minimal catalog -- just the kind + time_columns the compiler needs."""
    return {
        "metrics.daily_intake": {
            "table": "daily_intake",
            "schema": "metrics",
            "kind": "daily_metric",
            "time_columns": {"time_at": "date"},
        },
        "metrics.daily_outcomes": {
            "table": "daily_outcomes",
            "schema": "metrics",
            "kind": "daily_metric",
            "time_columns": {"time_at": "date"},
        },
    }


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------


class TestValidate:
    def test_valid_linear_recipe(self, catalog):
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(op_name="lag", params={"column": "caffeine_mg", "n": 1}, inputs=("intake",)),
            },
            final="lagged",
        )
        assert recipe.validate(catalog) == []

    def test_missing_final(self, catalog):
        recipe = Recipe(
            nodes={"intake": SourceRef(table="metrics.daily_intake")},
            final="bogus",
        )
        errors = recipe.validate(catalog)
        assert any("final node `bogus`" in e for e in errors)

    def test_missing_source_in_catalog(self, catalog):
        recipe = Recipe(
            nodes={"x": SourceRef(table="metrics.does_not_exist")},
            final="x",
        )
        errors = recipe.validate(catalog)
        assert any("not in catalog" in e for e in errors)

    def test_unknown_operation(self, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="multiply", params={}, inputs=("src",)),
            },
            final="x",
        )
        errors = recipe.validate(catalog)
        assert any("unknown operation `multiply`" in e for e in errors)

    def test_arity_mismatch_too_few(self, catalog):
        # join_as_of requires 2 inputs; passing 1 should be flagged
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("src",)),
            },
            final="x",
        )
        errors = recipe.validate(catalog)
        assert any("requires 2 input(s), got 1" in e for e in errors)

    def test_arity_mismatch_too_many(self, catalog):
        # lag requires 1 input; passing 2 should be flagged
        recipe = Recipe(
            nodes={
                "a": SourceRef(table="metrics.daily_intake"),
                "b": SourceRef(table="metrics.daily_outcomes"),
                "x": OpCall(op_name="lag", params={"column": "caffeine_mg"}, inputs=("a", "b")),
            },
            final="x",
        )
        errors = recipe.validate(catalog)
        assert any("requires 1 input(s), got 2" in e for e in errors)

    def test_dangling_input_ref(self, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="lag", params={"column": "caffeine_mg"}, inputs=("missing_node",)),
            },
            final="x",
        )
        errors = recipe.validate(catalog)
        assert any("references an undefined node" in e for e in errors)

    def test_cycle_detected(self, catalog):
        # a -> b -> a is a cycle
        recipe = Recipe(
            nodes={
                "a": OpCall(op_name="lag", params={"column": "caffeine_mg"}, inputs=("b",)),
                "b": OpCall(op_name="lag", params={"column": "caffeine_mg"}, inputs=("a",)),
            },
            final="a",
        )
        errors = recipe.validate(catalog)
        assert any("cycle" in e for e in errors)


# ----------------------------------------------------------------------
# Topological order determinism
# ----------------------------------------------------------------------


class TestTopologicalOrder:
    def test_deterministic_alphabetical(self, catalog):
        # Two independent sources should be peeled off in alphabetical order.
        recipe = Recipe(
            nodes={
                "z_intake": SourceRef(table="metrics.daily_intake"),
                "a_outcomes": SourceRef(table="metrics.daily_outcomes"),
                "joined": OpCall(
                    op_name="join_as_of",
                    params={"on": "date"},
                    inputs=("z_intake", "a_outcomes"),
                ),
            },
            final="joined",
        )
        order = recipe._topological_order()
        # Sources first (alphabetical), then the joined op
        assert order[0] == "a_outcomes"
        assert order[1] == "z_intake"
        assert order[2] == "joined"


# ----------------------------------------------------------------------
# Compilation -- end to end against real DuckDB
# ----------------------------------------------------------------------


class TestCompileLinear:
    def test_single_source(self, con, catalog):
        recipe = Recipe(
            nodes={"x": SourceRef(table="metrics.daily_intake")},
            final="x",
        )
        result = recipe.compile(con, catalog)
        assert result.kind == "daily_metric"
        assert result.table_ref == "metrics.daily_intake"
        df = result.expr.order_by("date").execute()
        assert len(df) == 5

    def test_lag_then_correlate(self, con, catalog):
        # Linear chain: source -> lag -> (no correlate yet, just lag)
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(op_name="lag", params={"column": "caffeine_mg", "n": 1}, inputs=("intake",)),
            },
            final="lagged",
        )
        result = recipe.compile(con, catalog)
        df = result.expr.order_by("date").execute()
        assert "caffeine_mg_lag1" in df.columns
        assert df["caffeine_mg_lag1"].iloc[1] == 200  # second row's lag = first row's value

    def test_validation_failure_propagates(self, con, catalog):
        recipe = Recipe(
            nodes={
                "src": SourceRef(table="metrics.daily_intake"),
                "x": OpCall(op_name="multiply", params={}, inputs=("src",)),
            },
            final="x",
        )
        with pytest.raises(RecipeError, match="unknown operation"):
            recipe.compile(con, catalog)


class TestCompileTwoBranch:
    """The canonical hypothesis shape: two parallel pipelines + correlate."""

    def test_perfect_anticorrelation_via_dag(self, con, catalog):
        # Two source branches, joined as-of, correlated
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "outcomes": SourceRef(table="metrics.daily_outcomes"),
                "joined": OpCall(
                    op_name="join_as_of",
                    params={"on": "date"},
                    inputs=("intake", "outcomes"),
                ),
                "result": OpCall(
                    op_name="correlate",
                    params={"x": "caffeine_mg", "y": "mood"},
                    inputs=("joined",),
                ),
            },
            final="result",
        )
        result = recipe.compile(con, catalog)
        assert result.kind == "scalar_result"
        df = result.expr.execute()
        # Linear data -> perfect anti-correlation
        assert df["corr"].iloc[0] == pytest.approx(-1.0, abs=0.01)

    def test_lag_then_join_then_correlate(self, con, catalog):
        # The full hypothesis-testing recipe from the design doc Part 4.
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "outcomes": SourceRef(table="metrics.daily_outcomes"),
                "lagged_intake": OpCall(
                    op_name="lag",
                    params={"column": "caffeine_mg", "n": 1},
                    inputs=("intake",),
                ),
                "joined": OpCall(
                    op_name="join_as_of",
                    params={"on": "date"},
                    inputs=("lagged_intake", "outcomes"),
                ),
                "result": OpCall(
                    op_name="correlate",
                    params={"x": "caffeine_mg_lag1", "y": "mood"},
                    inputs=("joined",),
                ),
            },
            final="result",
        )
        result = recipe.compile(con, catalog)
        assert result.kind == "scalar_result"
        df = result.expr.execute()
        # caffeine declines monotonically, mood rises monotonically.
        # Yesterday's caffeine vs today's mood -> still strongly anti-correlated
        # (but no longer exactly -1.0 because of the NULL first row).
        corr = df["corr"].iloc[0]
        assert corr is not None
        assert corr < -0.9  # strongly anti-correlated


# ----------------------------------------------------------------------
# to_sql convenience
# ----------------------------------------------------------------------


class TestToSql:
    def test_renders_select(self, con, catalog):
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(op_name="lag", params={"column": "caffeine_mg", "n": 1}, inputs=("intake",)),
            },
            final="lagged",
        )
        sql = recipe.to_sql(con, catalog)
        assert "LAG" in sql.upper()
        assert "caffeine_mg" in sql

    def test_two_branch_uses_join(self, con, catalog):
        recipe = Recipe(
            nodes={
                "a": SourceRef(table="metrics.daily_intake"),
                "b": SourceRef(table="metrics.daily_outcomes"),
                "joined": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
            },
            final="joined",
        )
        sql = recipe.to_sql(con, catalog)
        assert "JOIN" in sql.upper()


# ----------------------------------------------------------------------
# Param coercion: list -> tuple for frozen-dataclass operations
# ----------------------------------------------------------------------


class TestParamCoercion:
    def test_list_partition_by_coerced_to_tuple(self, con, catalog):
        # Recipes round-trip through JSON, where tuples become lists.
        # The compiler must coerce lists back to tuples before instantiating
        # frozen-dataclass operations (which use tuple fields for hashability).
        recipe = Recipe(
            nodes={
                "intake": SourceRef(table="metrics.daily_intake"),
                "lagged": OpCall(
                    op_name="lag",
                    params={"column": "caffeine_mg", "n": 1, "partition_by": []},
                    inputs=("intake",),
                ),
            },
            final="lagged",
        )
        # Should not raise about list-vs-tuple
        result = recipe.compile(con, catalog)
        assert "caffeine_mg_lag1" in result.expr.columns

    def test_can_construct_lag_directly(self):
        # Sanity: the operation classes really do require tuple, not list
        with pytest.raises(TypeError):  # frozen dataclass with mutable default
            hash(Lag(column="x", partition_by=[]))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
