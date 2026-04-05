from datetime import UTC, datetime, timedelta

import pytest

from shenas_pipes.core.cli import create_pipe_app
from shenas_pipes.core.utils import date_range, is_empty_response, resolve_start_date


class TestResolveStartDate:
    def test_iso_date(self) -> None:
        assert resolve_start_date("2026-01-15") == "2026-01-15"

    def test_days_ago(self) -> None:
        result = resolve_start_date("7 days ago")
        expected = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        assert result == expected

    def test_single_day_ago(self) -> None:
        result = resolve_start_date("1 day ago")
        expected = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
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


class TestCreatePipeApp:
    def test_creates_typer_app(self) -> None:
        app = create_pipe_app("Test commands.")
        assert app.info.help == "Test commands."
