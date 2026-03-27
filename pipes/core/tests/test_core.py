import duckdb
import pendulum
import pytest

from shenas_pipes.core.cli import create_pipe_app
from shenas_pipes.core.transform import MetricProviderBase
from shenas_pipes.core.utils import date_range, is_empty_response, resolve_start_date


class TestResolveStartDate:
    def test_iso_date(self) -> None:
        assert resolve_start_date("2026-01-15") == "2026-01-15"

    def test_days_ago(self) -> None:
        result = resolve_start_date("7 days ago")
        expected = pendulum.now().subtract(days=7).to_date_string()
        assert result == expected

    def test_single_day_ago(self) -> None:
        result = resolve_start_date("1 day ago")
        expected = pendulum.now().subtract(days=1).to_date_string()
        assert result == expected

    def test_invalid(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            resolve_start_date("yesterday")


class TestDateRange:
    def test_single_day(self) -> None:
        assert list(date_range("2026-03-15", "2026-03-15")) == ["2026-03-15"]

    def test_multi_day(self) -> None:
        assert list(date_range("2026-03-10", "2026-03-12")) == ["2026-03-10", "2026-03-11", "2026-03-12"]


class TestIsEmptyResponse:
    def test_none(self) -> None:
        assert is_empty_response(None) is True

    def test_empty(self) -> None:
        assert is_empty_response({}) is True

    def test_missing_sentinel(self) -> None:
        assert is_empty_response({"other": 1}) is True

    def test_has_sentinel(self) -> None:
        assert is_empty_response({"calendarDate": "2026-03-15"}) is False


class TestMetricProviderBase:
    def test_upsert(self) -> None:
        con = duckdb.connect(":memory:")
        con.execute("CREATE SCHEMA metrics")
        con.execute("CREATE TABLE metrics.test (date DATE, source VARCHAR, val INTEGER)")
        con.execute("INSERT INTO metrics.test VALUES ('2026-03-15', 'src', 1)")

        class TestProvider(MetricProviderBase):
            source = "src"

        provider = TestProvider()
        provider._upsert(con, "test", "INSERT INTO metrics.test VALUES ('2026-03-16', 'src', 2)")

        rows = con.execute("SELECT * FROM metrics.test").fetchall()
        assert len(rows) == 1
        assert str(rows[0][0]) == "2026-03-16"
        con.close()

    def test_upsert_only_deletes_own_source(self) -> None:
        con = duckdb.connect(":memory:")
        con.execute("CREATE SCHEMA metrics")
        con.execute("CREATE TABLE metrics.test (source VARCHAR, val INTEGER)")
        con.execute("INSERT INTO metrics.test VALUES ('other', 1), ('mine', 2)")

        class TestProvider(MetricProviderBase):
            source = "mine"

        provider = TestProvider()
        provider._upsert(con, "test", "INSERT INTO metrics.test VALUES ('mine', 3)")

        rows = con.execute("SELECT * FROM metrics.test ORDER BY source").fetchall()
        assert len(rows) == 2
        assert rows[0] == ("mine", 3)
        assert rows[1] == ("other", 1)
        con.close()


class TestCreatePipeApp:
    def test_creates_typer_app(self) -> None:
        app = create_pipe_app("Test commands.")
        assert app.info.help == "Test commands."
