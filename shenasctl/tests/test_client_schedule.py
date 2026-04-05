"""Tests for ShenasClient schedule methods."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from shenasctl.client import ShenasClient

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def client() -> Iterator[ShenasClient]:
    c = ShenasClient()
    yield c
    c.close()


class TestGetSyncSchedule:
    def test_calls_graphql(self, client: ShenasClient) -> None:
        schedule = [
            {"name": "garmin", "syncFrequency": 60, "syncedAt": None, "isDue": True},
            {"name": "lunchmoney", "syncFrequency": 120, "syncedAt": "2026-03-30", "isDue": False},
        ]
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": {"syncSchedule": schedule}}

        with patch.object(client._client, "post", return_value=mock_resp):
            result = client.get_sync_schedule()

        assert len(result) == 2
        assert result[0]["name"] == "garmin"
