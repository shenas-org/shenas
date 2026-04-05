from datetime import UTC, datetime, timedelta

import pytest

from shenas_pipes.core.utils import resolve_start_date


class TestResolveStartDate:
    def test_iso_date(self) -> None:
        assert resolve_start_date("2026-01-15") == "2026-01-15"

    def test_days_ago(self) -> None:
        result = resolve_start_date("90 days ago")
        expected = (datetime.now(UTC).date() - timedelta(days=90)).isoformat()
        assert result == expected

    def test_single_day_ago(self) -> None:
        result = resolve_start_date("1 day ago")
        expected = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        assert result == expected

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            resolve_start_date("last month")
