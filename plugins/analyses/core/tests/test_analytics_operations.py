"""Tests for the curated operation library.

End-to-end against a real in-memory DuckDB via Ibis. The tests cover:

- Each operation produces the expected SQL / result on real data
- Kind validation rejects type-mismatched inputs (e.g. ``Lag`` on a
  ``DimensionTable``)
- Two-branch correlation works through ``JoinAsOf`` + ``Correlate``,
  which is the most common hypothesis shape
"""

from __future__ import annotations

import ibis
import pytest
from shenas_analyses.core.analytics import (
    Correlate,
    JoinAsOf,
    Lag,
    OperationError,
    RecipeNode,
    Resample,
    Rolling,
)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def con():
    """A fresh in-memory DuckDB Ibis connection per test."""
    return ibis.duckdb.connect(":memory:")


@pytest.fixture
def daily_intake(con):
    """A small ``daily_metric`` style table: per-day caffeine intake.

    Linear by 50 mg/day so the perfect-anticorrelation test gets exactly -1.0.
    """
    con.raw_sql("CREATE TABLE daily_intake (date DATE, caffeine_mg DOUBLE)")
    con.raw_sql(
        "INSERT INTO daily_intake VALUES "
        "('2026-04-01', 200), "
        "('2026-04-02', 150), "
        "('2026-04-03', 100), "
        "('2026-04-04', 50), "
        "('2026-04-05', 0)"
    )
    return RecipeNode(
        expr=con.table("daily_intake"),
        kind="daily_metric",
        time_columns={"time_at": "date"},
        table_ref="metrics.daily_intake",
    )


@pytest.fixture
def daily_outcomes(con):
    """A second ``daily_metric`` table: per-day mood score."""
    con.raw_sql("CREATE TABLE daily_outcomes (date DATE, mood DOUBLE)")
    con.raw_sql(
        "INSERT INTO daily_outcomes VALUES "
        "('2026-04-01', 5), "
        "('2026-04-02', 6), "
        "('2026-04-03', 7), "
        "('2026-04-04', 8), "
        "('2026-04-05', 9)"
    )
    return RecipeNode(
        expr=con.table("daily_outcomes"),
        kind="daily_metric",
        time_columns={"time_at": "date"},
        table_ref="metrics.daily_outcomes",
    )


@pytest.fixture
def hourly_events(con):
    """A finer-grained ``event`` table: hourly heart-rate readings."""
    con.raw_sql("CREATE TABLE hourly_hr (ts TIMESTAMP, bpm DOUBLE)")
    con.raw_sql(
        "INSERT INTO hourly_hr VALUES "
        "('2026-04-01 06:00', 60), ('2026-04-01 12:00', 80), ('2026-04-01 18:00', 70), "
        "('2026-04-02 06:00', 62), ('2026-04-02 12:00', 78), ('2026-04-02 18:00', 72), "
        "('2026-04-03 06:00', 65), ('2026-04-03 12:00', 85), ('2026-04-03 18:00', 75)"
    )
    return RecipeNode(
        expr=con.table("hourly_hr"),
        kind="event",
        time_columns={"time_at": "ts"},
        table_ref="strava.hourly_hr",
    )


@pytest.fixture
def fake_dimension(con):
    """A fake SCD2 dimension to test kind rejection."""
    con.raw_sql("CREATE TABLE my_dim (id INTEGER, name VARCHAR)")
    return RecipeNode(
        expr=con.table("my_dim"),
        kind="dimension",
        time_columns={},
        table_ref="src.my_dim",
    )


# ----------------------------------------------------------------------
# Lag
# ----------------------------------------------------------------------


class TestLag:
    def test_adds_lag_column(self, daily_intake):
        result = Lag("caffeine_mg", n=1).apply(daily_intake)
        df = result.expr.order_by("date").execute()
        assert "caffeine_mg_lag1" in df.columns
        # First row has NULL lag; second row's lag = first row's value
        assert df["caffeine_mg_lag1"].iloc[0] is None or df["caffeine_mg_lag1"].iloc[0] != df["caffeine_mg_lag1"].iloc[0]
        assert df["caffeine_mg_lag1"].iloc[1] == 200
        assert df["caffeine_mg_lag1"].iloc[2] == 150

    def test_kind_propagates(self, daily_intake):
        result = Lag("caffeine_mg", n=1).apply(daily_intake)
        assert result.kind == "daily_metric"

    def test_rejects_dimension(self, fake_dimension):
        with pytest.raises(OperationError, match="cannot apply to a `dimension` table"):
            Lag("name", n=1).apply(fake_dimension)

    def test_rejects_unknown_column(self, daily_intake):
        with pytest.raises(OperationError, match="column `nonexistent` not in"):
            Lag("nonexistent", n=1).apply(daily_intake)

    def test_explicit_order_by(self, hourly_events):
        # ts is the inferred time_at -- this just confirms the override path works
        result = Lag("bpm", n=1, order_by="ts").apply(hourly_events)
        assert "bpm_lag1" in result.expr.columns


# ----------------------------------------------------------------------
# Rolling
# ----------------------------------------------------------------------


class TestRolling:
    def test_rolling_average(self, daily_intake):
        result = Rolling("caffeine_mg", window=3, fn="avg").apply(daily_intake)
        df = result.expr.order_by("date").execute()
        assert "caffeine_mg_avg3" in df.columns
        # Row 3 = avg(200, 150, 100) = 150
        assert df["caffeine_mg_avg3"].iloc[2] == pytest.approx(150.0)
        # Row 5 = avg(100, 50, 0) = 50
        assert df["caffeine_mg_avg3"].iloc[4] == pytest.approx(50.0)

    def test_rolling_sum(self, daily_intake):
        result = Rolling("caffeine_mg", window=2, fn="sum").apply(daily_intake)
        df = result.expr.order_by("date").execute()
        assert df["caffeine_mg_sum2"].iloc[1] == pytest.approx(350.0)  # 200 + 150

    def test_rejects_unsupported_fn(self, daily_intake):
        with pytest.raises(OperationError, match="unsupported fn `median`"):
            Rolling("caffeine_mg", window=3, fn="median").apply(daily_intake)

    def test_rejects_zero_window(self, daily_intake):
        with pytest.raises(OperationError, match="window must be >= 1"):
            Rolling("caffeine_mg", window=0).apply(daily_intake)

    def test_rejects_dimension(self, fake_dimension):
        with pytest.raises(OperationError, match="cannot apply to a `dimension` table"):
            Rolling("name", window=3).apply(fake_dimension)


# ----------------------------------------------------------------------
# Resample
# ----------------------------------------------------------------------


class TestResample:
    def test_event_to_daily(self, hourly_events):
        result = Resample(grain="day", aggregations=(("bpm", "avg"),)).apply(hourly_events)
        assert result.kind == "daily_metric"
        df = result.expr.order_by("day").execute()
        # 3 days, each with 3 hourly readings
        assert len(df) == 3
        # Day 1: avg(60, 80, 70) = 70
        assert df["bpm_avg"].iloc[0] == pytest.approx(70.0)

    def test_kind_shifts_to_metric(self, hourly_events):
        result = Resample(grain="week", aggregations=(("bpm", "avg"),)).apply(hourly_events)
        assert result.kind == "weekly_metric"
        assert result.time_columns == {"time_at": "week"}

    def test_multiple_aggregations(self, hourly_events):
        result = Resample(grain="day", aggregations=(("bpm", "avg"), ("bpm", "max"))).apply(hourly_events)
        df = result.expr.order_by("day").execute()
        assert "bpm_avg" in df.columns
        assert "bpm_max" in df.columns
        assert df["bpm_max"].iloc[0] == 80  # max of 60, 80, 70

    def test_rejects_bad_grain(self, hourly_events):
        with pytest.raises(OperationError, match="grain must be one of"):
            Resample(grain="hour", aggregations=(("bpm", "avg"),)).apply(hourly_events)

    def test_rejects_no_aggregations(self, hourly_events):
        with pytest.raises(OperationError, match="at least one aggregation"):
            Resample(grain="day").apply(hourly_events)

    def test_rejects_unknown_column(self, hourly_events):
        with pytest.raises(OperationError, match="column `bogus` not in"):
            Resample(grain="day", aggregations=(("bogus", "avg"),)).apply(hourly_events)


# ----------------------------------------------------------------------
# JoinAsOf
# ----------------------------------------------------------------------


class TestJoinAsOf:
    def test_two_daily_metrics(self, daily_intake, daily_outcomes):
        joined = JoinAsOf(on="date").apply(daily_intake, daily_outcomes)
        df = joined.expr.order_by("date").execute()
        assert "caffeine_mg" in df.columns
        assert "mood" in df.columns
        assert len(df) == 5  # one row per left date

    def test_left_kind_propagates(self, daily_intake, daily_outcomes):
        joined = JoinAsOf(on="date").apply(daily_intake, daily_outcomes)
        assert joined.kind == "daily_metric"

    def test_rejects_missing_left_column(self, daily_intake, daily_outcomes):
        with pytest.raises(OperationError, match="not in left side"):
            JoinAsOf(on="bogus").apply(daily_intake, daily_outcomes)

    def test_rejects_missing_right_column(self, daily_intake, daily_outcomes):
        # Use a right node that doesn't have the same join key
        bad_right = RecipeNode(
            expr=daily_outcomes.expr.drop("date"),
            kind="daily_metric",
            table_ref="metrics.no_date",
        )
        with pytest.raises(OperationError, match="not in right side"):
            JoinAsOf(on="date").apply(daily_intake, bad_right)


# ----------------------------------------------------------------------
# Correlate
# ----------------------------------------------------------------------


class TestCorrelate:
    def test_perfect_anticorrelation(self, daily_intake, daily_outcomes):
        # caffeine declines monotonically while mood rises monotonically -> -1.0
        joined = JoinAsOf(on="date").apply(daily_intake, daily_outcomes)
        result = Correlate(x="caffeine_mg", y="mood").apply(joined)
        df = result.expr.execute()
        assert df["corr"].iloc[0] == pytest.approx(-1.0, abs=0.01)

    def test_kind_becomes_scalar(self, daily_intake, daily_outcomes):
        joined = JoinAsOf(on="date").apply(daily_intake, daily_outcomes)
        result = Correlate(x="caffeine_mg", y="mood").apply(joined)
        assert result.kind == "scalar_result"
        assert result.time_columns == {}

    def test_rejects_missing_columns(self, daily_intake):
        with pytest.raises(OperationError, match="`bogus` not in"):
            Correlate(x="bogus", y="caffeine_mg").apply(daily_intake)


# ----------------------------------------------------------------------
# End-to-end: the canonical "two parallel pipelines + correlate" recipe
# from Part 4 of the design doc.
# ----------------------------------------------------------------------


class TestTwoBranchCorrelationRecipe:
    def test_lag_then_resample_then_correlate(self, con):
        """Build a small daily table and run the full hypothesis-testing
        recipe shape end to end.

        Hypothesis: caffeine intake one day -> lower mood the next day.
        Recipe:
          1. lag(daily_intake.caffeine_mg, n=1) -> caffeine_mg_lag1
          2. join_as_of with daily_outcomes on date
          3. correlate caffeine_mg_lag1 vs mood
        """
        con.raw_sql("CREATE TABLE intake (date DATE, caffeine_mg DOUBLE)")
        con.raw_sql(
            "INSERT INTO intake VALUES "
            "('2026-04-01', 300), ('2026-04-02', 0), ('2026-04-03', 300), "
            "('2026-04-04', 0), ('2026-04-05', 300), ('2026-04-06', 0)"
        )
        con.raw_sql("CREATE TABLE outcomes (date DATE, mood DOUBLE)")
        con.raw_sql(
            "INSERT INTO outcomes VALUES "
            "('2026-04-01', 5), ('2026-04-02', 3), ('2026-04-03', 6), "
            "('2026-04-04', 3), ('2026-04-05', 6), ('2026-04-06', 3)"
        )

        intake = RecipeNode(
            expr=con.table("intake"),
            kind="daily_metric",
            time_columns={"time_at": "date"},
            table_ref="metrics.intake",
        )
        outcomes = RecipeNode(
            expr=con.table("outcomes"),
            kind="daily_metric",
            time_columns={"time_at": "date"},
            table_ref="metrics.outcomes",
        )

        # Step 1: lag caffeine by 1 day
        lagged = Lag("caffeine_mg", n=1).apply(intake)

        # Step 2: join with outcomes on date
        joined = JoinAsOf(on="date").apply(lagged, outcomes)

        # Step 3: correlate the lagged caffeine with same-day mood
        correlated = Correlate(x="caffeine_mg_lag1", y="mood").apply(joined)

        df = correlated.expr.execute()
        # When yesterday had caffeine (300mg), today's mood is 3.
        # When yesterday had no caffeine (0mg), today's mood is 6.
        # Previous-day caffeine -> lower mood today: perfect anti-correlation.
        assert df["corr"].iloc[0] == pytest.approx(-1.0, abs=0.01)
