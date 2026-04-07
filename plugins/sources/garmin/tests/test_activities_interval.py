"""Unit tests for the Garmin Activities IntervalTable reclassification."""

from __future__ import annotations

from unittest.mock import MagicMock

from shenas_sources.garmin.tables import Activities


class TestActivitiesInterval:
    def test_kind_is_interval(self) -> None:
        assert Activities.kind == "interval"
        assert Activities.time_start == "startTimeLocal"
        assert Activities.time_end == "end_time_local"

    def test_extract_computes_end_time_from_start_plus_duration(self) -> None:
        client = MagicMock()
        client.get_activities_by_date.return_value = [
            {
                "activityId": 999,
                "activityName": "Morning Run",
                "startTimeLocal": "2026-04-07 08:00:00",
                "duration": 1850.0,  # 30m 50s
                "distance": 5000.0,
            }
        ]

        rows = list(Activities.extract(client, start_date="2026-04-01"))
        assert len(rows) == 1
        assert rows[0]["activity_id"] == "999"
        assert rows[0]["end_time_local"] is not None
        # 08:00:00 + 1850 seconds = 08:30:50
        assert rows[0]["end_time_local"].endswith("08:30:50")

    def test_extract_handles_missing_duration(self) -> None:
        client = MagicMock()
        client.get_activities_by_date.return_value = [
            {"activityId": 1, "startTimeLocal": "2026-04-07 08:00:00", "duration": None},
        ]
        rows = list(Activities.extract(client, start_date="2026-04-01"))
        assert rows[0]["end_time_local"] is None

    def test_extract_handles_missing_start(self) -> None:
        client = MagicMock()
        client.get_activities_by_date.return_value = [
            {"activityId": 1, "startTimeLocal": None, "duration": 600.0},
        ]
        rows = list(Activities.extract(client, start_date="2026-04-01"))
        assert rows[0]["end_time_local"] is None
