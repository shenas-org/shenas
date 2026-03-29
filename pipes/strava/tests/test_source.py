from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from shenas_pipes.strava.source import activities, athlete, athlete_stats


def _mock_activity(**overrides: Any) -> MagicMock:
    """Create a mock stravalib SummaryActivity."""
    defaults: dict[str, Any] = {
        "id": 123,
        "name": "Morning Run",
        "type": "Run",
        "sport_type": "Run",
        "start_date": datetime(2026, 3, 28, 7, 0, tzinfo=timezone.utc),
        "start_date_local": datetime(2026, 3, 28, 9, 0),
        "timezone": "(GMT+02:00) Europe/Berlin",
        "distance": MagicMock(magnitude=5000.0),
        "moving_time": MagicMock(magnitude=1800),
        "elapsed_time": MagicMock(magnitude=1900),
        "total_elevation_gain": MagicMock(magnitude=50.0),
        "average_speed": MagicMock(magnitude=2.78),
        "max_speed": MagicMock(magnitude=3.5),
        "average_heartrate": 145.0,
        "max_heartrate": 170,
        "average_cadence": None,
        "average_watts": None,
        "kilojoules": MagicMock(magnitude=1464.0),
        "has_heartrate": True,
        "suffer_score": 42,
        "trainer": False,
        "commute": False,
        "manual": False,
        "gear_id": "g123",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestActivities:
    def test_yields_activities(self) -> None:
        client = MagicMock()
        client.get_activities.return_value = [_mock_activity()]

        results = list(activities(client, "2026-03-01"))
        assert len(results) == 1
        assert results[0]["id"] == 123
        assert results[0]["distance_m"] == 5000.0
        assert results[0]["average_heartrate"] == 145.0

    def test_empty_response(self) -> None:
        client = MagicMock()
        client.get_activities.return_value = []

        results = list(activities(client, "2026-03-01"))
        assert len(results) == 0


class TestAthlete:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        mock_athlete = MagicMock()
        mock_athlete.id = 42
        mock_athlete.username = "testuser"
        mock_athlete.firstname = "Test"
        mock_athlete.lastname = "User"
        mock_athlete.city = "Berlin"
        mock_athlete.state = "Berlin"
        mock_athlete.country = "Germany"
        mock_athlete.sex = "M"
        mock_athlete.weight = MagicMock(magnitude=75.0)
        mock_athlete.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        client.get_athlete.return_value = mock_athlete

        results = list(athlete(client))
        assert len(results) == 1
        assert results[0]["username"] == "testuser"
        assert results[0]["weight"] == 75.0


class TestAthleteStats:
    def test_yields_stat_rows(self) -> None:
        client = MagicMock()
        mock_athlete = MagicMock()
        mock_athlete.id = 42
        client.get_athlete.return_value = mock_athlete

        mock_stats = MagicMock()
        run_totals = MagicMock()
        run_totals.count = 5
        run_totals.distance = MagicMock(magnitude=25000)
        run_totals.moving_time = MagicMock(magnitude=9000)
        run_totals.elapsed_time = MagicMock(magnitude=9500)
        run_totals.elevation_gain = MagicMock(magnitude=200)
        run_totals.achievement_count = 2
        mock_stats.recent_run_totals = run_totals

        ride_totals = MagicMock()
        ride_totals.count = 10
        ride_totals.distance = MagicMock(magnitude=500000)
        ride_totals.moving_time = MagicMock(magnitude=72000)
        ride_totals.elapsed_time = MagicMock(magnitude=80000)
        ride_totals.elevation_gain = MagicMock(magnitude=3000)
        ride_totals.achievement_count = 5
        mock_stats.ytd_ride_totals = ride_totals

        # Set remaining totals to None
        for attr in (
            "recent_ride_totals",
            "recent_swim_totals",
            "ytd_run_totals",
            "ytd_swim_totals",
            "all_run_totals",
            "all_ride_totals",
            "all_swim_totals",
        ):
            setattr(mock_stats, attr, None)

        client.get_athlete_stats.return_value = mock_stats

        results = list(athlete_stats(client))
        assert len(results) == 2
        assert results[0]["period"] == "recent"
        assert results[0]["sport"] == "run"
        assert results[1]["period"] == "ytd"
        assert results[1]["sport"] == "ride"
