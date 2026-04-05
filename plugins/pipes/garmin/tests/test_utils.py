from datetime import UTC, datetime, timedelta

import pytest

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

    def test_with_whitespace(self) -> None:
        result = resolve_start_date("  30 days ago  ")
        expected = (datetime.now(UTC).date() - timedelta(days=30)).isoformat()
        assert result == expected

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            resolve_start_date("last week")

    def test_partial_date(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            resolve_start_date("2026-01")


class TestDateRange:
    def test_single_day(self) -> None:
        dates = list(date_range("2026-03-15", "2026-03-15"))
        assert dates == ["2026-03-15"]

    def test_multi_day(self) -> None:
        dates = list(date_range("2026-03-10", "2026-03-13"))
        assert dates == ["2026-03-10", "2026-03-11", "2026-03-12", "2026-03-13"]

    def test_no_end_uses_today(self) -> None:
        today = datetime.now(UTC).date().isoformat()
        dates = list(date_range(today))
        assert len(dates) == 1
        assert dates[0] == today


class TestIsEmptyResponse:
    def test_none(self) -> None:
        assert is_empty_response(None) is True

    def test_empty_dict(self) -> None:
        assert is_empty_response({}) is True

    def test_missing_sentinel(self) -> None:
        assert is_empty_response({"other": "value"}) is True

    def test_has_sentinel(self) -> None:
        assert is_empty_response({"calendarDate": "2026-03-15"}) is False

    def test_custom_sentinel(self) -> None:
        assert is_empty_response({"totalSteps": 5000}, sentinel_key="totalSteps") is False

    def test_sentinel_is_none(self) -> None:
        assert is_empty_response({"calendarDate": None}) is True
