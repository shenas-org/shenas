"""Tests for the structured SQL query builder."""

import pytest
from shenas_transformers.sql.query import (
    Filter,
    LagConfig,
    OrderBy,
    ResampleConfig,
    SelectColumn,
    SelectQuery,
    _validate_identifier,
)


class TestValidateIdentifier:
    def test_valid_identifiers(self):
        assert _validate_identifier("name") == "name"
        assert _validate_identifier("_private") == "_private"
        assert _validate_identifier("col_123") == "col_123"
        assert _validate_identifier("CamelCase") == "CamelCase"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("")

    def test_rejects_starts_with_digit(self):
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("1column")

    def test_rejects_special_characters(self):
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("col-name")
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("col.name")
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("col name")

    def test_rejects_sql_injection_attempts(self):
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("col; DROP TABLE")
        with pytest.raises(ValueError, match="Invalid identifier"):
            _validate_identifier("col'--")


class TestSelectColumn:
    def test_simple_column(self):
        col = SelectColumn(name="id")
        assert col.to_sql() == "id"

    def test_column_with_alias(self):
        col = SelectColumn(name="visit_time", alias="time_at")
        assert col.to_sql() == "visit_time AS time_at"

    def test_column_with_aggregate(self):
        col = SelectColumn(name="bytes", aggregate="sum")
        assert col.to_sql() == "SUM(bytes) AS bytes_sum"

    def test_column_with_aggregate_and_alias(self):
        col = SelectColumn(name="bytes", aggregate="sum", alias="total_bytes")
        assert col.to_sql() == "SUM(bytes) AS total_bytes"

    def test_all_valid_aggregates(self):
        for agg in ("sum", "avg", "count", "min", "max"):
            col = SelectColumn(name="value", aggregate=agg)
            sql = col.to_sql()
            assert agg.upper() in sql

    def test_invalid_aggregate(self):
        col = SelectColumn(name="value", aggregate="MEDIAN")
        with pytest.raises(ValueError, match="Invalid aggregate"):
            col.to_sql()

    def test_invalid_column_name(self):
        col = SelectColumn(name="bad name")
        with pytest.raises(ValueError, match="Invalid identifier"):
            col.to_sql()

    def test_invalid_alias(self):
        col = SelectColumn(name="ok", alias="bad alias")
        with pytest.raises(ValueError, match="Invalid identifier"):
            col.to_sql()


class TestFilter:
    def test_eq(self):
        filt = Filter(column="status", operator="eq", value="active")
        sql, params = filt.to_sql()
        assert sql == "status = ?"
        assert params == ["active"]

    def test_neq(self):
        filt = Filter(column="status", operator="neq", value="deleted")
        sql, params = filt.to_sql()
        assert sql == "status != ?"
        assert params == ["deleted"]

    def test_gt_lt_gte_lte(self):
        for operator, expected in [("gt", ">"), ("lt", "<"), ("gte", ">="), ("lte", "<=")]:
            filt = Filter(column="age", operator=operator, value="18")
            sql, params = filt.to_sql()
            assert sql == f"age {expected} ?"
            assert params == ["18"]

    def test_contains(self):
        filt = Filter(column="title", operator="contains", value="test")
        sql, params = filt.to_sql()
        assert sql == "title LIKE ?"
        assert params == ["%test%"]

    def test_starts_with(self):
        filt = Filter(column="url", operator="starts_with", value="https")
        sql, params = filt.to_sql()
        assert sql == "url LIKE ?"
        assert params == ["https%"]

    def test_is_null(self):
        filt = Filter(column="end_time", operator="is_null")
        sql, params = filt.to_sql()
        assert sql == "end_time IS NULL"
        assert params == []

    def test_is_not_null(self):
        filt = Filter(column="end_time", operator="is_not_null")
        sql, params = filt.to_sql()
        assert sql == "end_time IS NOT NULL"
        assert params == []

    def test_invalid_operator(self):
        filt = Filter(column="x", operator="BETWEEN")
        with pytest.raises(ValueError, match="Invalid operator"):
            filt.to_sql()

    def test_invalid_column(self):
        filt = Filter(column="bad col", operator="eq", value="x")
        with pytest.raises(ValueError, match="Invalid identifier"):
            filt.to_sql()


class TestOrderBy:
    def test_asc(self):
        ob = OrderBy(column="name", direction="asc")
        assert ob.to_sql() == "name ASC"

    def test_desc(self):
        ob = OrderBy(column="created_at", direction="desc")
        assert ob.to_sql() == "created_at DESC"

    def test_invalid_direction(self):
        ob = OrderBy(column="name", direction="sideways")
        with pytest.raises(ValueError, match="Invalid direction"):
            ob.to_sql()

    def test_invalid_column(self):
        ob = OrderBy(column="bad col", direction="asc")
        with pytest.raises(ValueError, match="Invalid identifier"):
            ob.to_sql()


class TestSelectQuery:
    def test_simple_select(self):
        query = SelectQuery(columns=[SelectColumn(name="id"), SelectColumn(name="name")])
        sql, params = query.to_sql("my_table")
        assert sql == "SELECT id, name\nFROM my_table"
        assert params == []

    def test_with_filter(self):
        query = SelectQuery(
            columns=[SelectColumn(name="id")],
            filters=[Filter(column="status", operator="eq", value="active")],
        )
        sql, params = query.to_sql("users")
        assert "WHERE status = ?" in sql
        assert params == ["active"]

    def test_with_multiple_filters(self):
        query = SelectQuery(
            columns=[SelectColumn(name="id")],
            filters=[
                Filter(column="age", operator="gte", value="18"),
                Filter(column="status", operator="neq", value="banned"),
            ],
        )
        sql, params = query.to_sql("users")
        assert "WHERE age >= ? AND status != ?" in sql
        assert params == ["18", "banned"]

    def test_with_group_by(self):
        query = SelectQuery(
            columns=[
                SelectColumn(name="category"),
                SelectColumn(name="amount", aggregate="sum", alias="total"),
            ],
            group_by=["category"],
        )
        sql, _params = query.to_sql("transactions")
        assert "GROUP BY category" in sql
        assert "SUM(amount) AS total" in sql

    def test_with_order_by(self):
        query = SelectQuery(
            columns=[SelectColumn(name="name")],
            order_by=[OrderBy(column="name", direction="asc")],
        )
        sql, _ = query.to_sql("items")
        assert "ORDER BY name ASC" in sql

    def test_with_limit(self):
        query = SelectQuery(
            columns=[SelectColumn(name="id")],
            limit=100,
        )
        sql, _ = query.to_sql("items")
        assert "LIMIT 100" in sql

    def test_full_query(self):
        query = SelectQuery(
            columns=[
                SelectColumn(name="category"),
                SelectColumn(name="amount", aggregate="sum", alias="total"),
            ],
            filters=[Filter(column="status", operator="eq", value="completed")],
            group_by=["category"],
            order_by=[OrderBy(column="total", direction="desc")],
            limit=10,
        )
        sql, params = query.to_sql('"schema"."table"')
        assert sql.startswith("SELECT category, SUM(amount) AS total")
        assert 'FROM "schema"."table"' in sql
        assert "WHERE status = ?" in sql
        assert "GROUP BY category" in sql
        assert "ORDER BY total DESC" in sql
        assert "LIMIT 10" in sql
        assert params == ["completed"]

    def test_empty_columns_raises(self):
        query = SelectQuery(columns=[])
        with pytest.raises(ValueError, match="at least one column"):
            query.to_sql("t")

    def test_to_dict_roundtrip(self):
        original = SelectQuery(
            columns=[SelectColumn(name="id", alias="pk"), SelectColumn(name="val", aggregate="avg")],
            filters=[Filter(column="x", operator="gt", value="5")],
            group_by=["pk"],
            order_by=[OrderBy(column="pk", direction="asc")],
            limit=50,
        )
        data = original.to_dict()
        restored = SelectQuery.from_dict(data)
        assert len(restored.columns) == 2
        assert restored.columns[0].alias == "pk"
        assert restored.columns[1].aggregate == "avg"
        assert len(restored.filters) == 1
        assert restored.filters[0].operator == "gt"
        assert restored.group_by == ["pk"]
        assert len(restored.order_by) == 1
        assert restored.limit == 50

    def test_from_dict_empty(self):
        query = SelectQuery.from_dict({})
        assert query.columns == []
        assert query.filters == []
        assert query.group_by == []
        assert query.order_by == []
        assert query.limit is None

    def test_from_dict_limit_as_string(self):
        query = SelectQuery.from_dict({"columns": [{"name": "id"}], "limit": "25"})
        assert query.limit == 25

    def test_invalid_group_by_identifier(self):
        query = SelectQuery(
            columns=[SelectColumn(name="x")],
            group_by=["bad col"],
        )
        with pytest.raises(ValueError, match="Invalid identifier"):
            query.to_sql("t")


class TestLagConfig:
    def test_simple_lag(self):
        lag = LagConfig(column="value", periods=1)
        sql = lag.to_sql(time_col="date")
        assert sql == "LAG(value, 1) OVER (ORDER BY date) AS value_lag1"

    def test_lag_with_custom_order(self):
        lag = LagConfig(column="hrv", periods=3, order_by="timestamp")
        sql = lag.to_sql()
        assert sql == "LAG(hrv, 3) OVER (ORDER BY timestamp) AS hrv_lag3"

    def test_lag_defaults_to_column_when_no_time_col(self):
        lag = LagConfig(column="value", periods=1)
        sql = lag.to_sql()
        assert "ORDER BY value" in sql

    def test_lag_invalid_column(self):
        lag = LagConfig(column="bad col", periods=1)
        with pytest.raises(ValueError, match="Invalid identifier"):
            lag.to_sql()


class TestResampleConfig:
    def test_valid_grains(self):
        for grain in ("day", "week", "month", "year", "hour"):
            config = ResampleConfig(grain=grain, time_column="date")
            config.validate()  # should not raise

    def test_invalid_grain(self):
        config = ResampleConfig(grain="quarter", time_column="date")
        with pytest.raises(ValueError, match="Invalid grain"):
            config.validate()

    def test_valid_funcs(self):
        for func in ("avg", "sum", "min", "max", "count", "first", "last"):
            config = ResampleConfig(grain="week", time_column="date", func=func)
            config.validate()

    def test_invalid_func(self):
        config = ResampleConfig(grain="week", time_column="date", func="median")
        with pytest.raises(ValueError, match="Invalid resample function"):
            config.validate()


class TestSelectQueryWithLag:
    def test_lag_columns_added(self):
        query = SelectQuery(
            columns=[SelectColumn(name="date"), SelectColumn(name="hrv")],
            lags=[LagConfig(column="hrv", periods=1, order_by="date")],
        )
        sql, _ = query.to_sql("metrics")
        assert "LAG(hrv, 1) OVER (ORDER BY date) AS hrv_lag1" in sql

    def test_multiple_lags(self):
        query = SelectQuery(
            columns=[SelectColumn(name="date"), SelectColumn(name="hrv")],
            lags=[
                LagConfig(column="hrv", periods=1, order_by="date"),
                LagConfig(column="hrv", periods=7, order_by="date"),
            ],
        )
        sql, _ = query.to_sql("metrics")
        assert "hrv_lag1" in sql
        assert "hrv_lag7" in sql


class TestSelectQueryWithResample:
    def test_resample_weekly(self):
        query = SelectQuery(
            columns=[SelectColumn(name="date"), SelectColumn(name="hrv")],
            resample=ResampleConfig(grain="week", time_column="date"),
        )
        sql, _ = query.to_sql("daily_vitals")
        assert "DATE_TRUNC('week', date) AS date" in sql
        assert "AVG(hrv) AS hrv" in sql
        assert "GROUP BY DATE_TRUNC('week', date)" in sql

    def test_resample_with_group_by(self):
        query = SelectQuery(
            columns=[
                SelectColumn(name="date"),
                SelectColumn(name="source"),
                SelectColumn(name="amount"),
            ],
            group_by=["source"],
            resample=ResampleConfig(grain="month", time_column="date", func="sum"),
        )
        sql, _ = query.to_sql("transactions")
        assert "DATE_TRUNC('month', date) AS date" in sql
        assert "SUM(amount) AS amount" in sql
        assert "source" in sql
        # source should be in GROUP BY but not aggregated
        assert "GROUP BY" in sql

    def test_resample_roundtrip(self):
        original = SelectQuery(
            columns=[SelectColumn(name="date"), SelectColumn(name="value")],
            resample=ResampleConfig(grain="week", time_column="date"),
            lags=[LagConfig(column="value", periods=1)],
        )
        data = original.to_dict()
        restored = SelectQuery.from_dict(data)
        assert restored.resample is not None
        assert restored.resample.grain == "week"
        assert len(restored.lags) == 1
        assert restored.lags[0].periods == 1
