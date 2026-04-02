"""Tests for ShenasClient schedule methods."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from cli.client import ShenasClient


@pytest.fixture()
def client() -> Iterator[ShenasClient]:
    c = ShenasClient()
    yield c
    c.close()


class TestGetSyncSchedule:
    def test_calls_get(self, client: ShenasClient) -> None:
        schedule = [
            {"name": "garmin", "sync_frequency": 60, "synced_at": None, "is_due": True},
            {"name": "lunchmoney", "sync_frequency": 120, "synced_at": "2026-03-30", "is_due": False},
        ]
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = schedule

        with patch.object(client._client, "request", return_value=mock_resp):
            result = client.get_sync_schedule()

        assert len(result) == 2
        assert result[0]["name"] == "garmin"
