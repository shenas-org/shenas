from __future__ import annotations

from unittest.mock import MagicMock

from shenas_pipes.strava.source import activities, athlete, athlete_stats


class TestActivities:
    def test_yields_activities(self) -> None:
        client = MagicMock()
        client.get_activities.return_value = [
            {
                "id": 123,
                "name": "Morning Run",
                "type": "Run",
                "sport_type": "Run",
                "start_date": "2026-03-28T07:00:00Z",
                "start_date_local": "2026-03-28T09:00:00Z",
                "timezone": "(GMT+02:00) Europe/Berlin",
                "distance": 5000.0,
                "moving_time": 1800,
                "elapsed_time": 1900,
                "total_elevation_gain": 50.0,
                "average_speed": 2.78,
                "max_speed": 3.5,
                "average_heartrate": 145.0,
                "max_heartrate": 170,
                "calories": 350.0,
                "has_heartrate": True,
            },
        ]

        results = list(activities(client, "2026-03-01"))
        assert len(results) == 1
        assert results[0]["id"] == 123
        assert results[0]["distance_m"] == 5000.0
        assert results[0]["average_heartrate"] == 145.0

    def test_paginates(self) -> None:
        client = MagicMock()
        page1 = [{"id": i, "start_date": "2026-03-28T07:00:00Z"} for i in range(200)]
        page2 = [{"id": 200, "start_date": "2026-03-29T07:00:00Z"}]
        client.get_activities.side_effect = [page1, page2]

        results = list(activities(client, "2026-03-01"))
        assert len(results) == 201
        assert client.get_activities.call_count == 2


class TestAthlete:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = {
            "id": 42,
            "username": "testuser",
            "firstname": "Test",
            "lastname": "User",
            "city": "Berlin",
            "state": "Berlin",
            "country": "Germany",
            "sex": "M",
            "weight": 75.0,
            "created_at": "2020-01-01T00:00:00Z",
        }

        results = list(athlete(client))
        assert len(results) == 1
        assert results[0]["username"] == "testuser"
        assert results[0]["weight"] == 75.0


class TestAthleteStats:
    def test_yields_stat_rows(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = {"id": 42}
        client.get_athlete_stats.return_value = {
            "recent_run_totals": {
                "count": 5,
                "distance": 25000,
                "moving_time": 9000,
                "elapsed_time": 9500,
                "elevation_gain": 200,
                "achievement_count": 2,
            },
            "ytd_ride_totals": {
                "count": 10,
                "distance": 500000,
                "moving_time": 72000,
                "elapsed_time": 80000,
                "elevation_gain": 3000,
                "achievement_count": 5,
            },
        }

        results = list(athlete_stats(client))
        assert len(results) == 2
        assert results[0]["period"] == "recent"
        assert results[0]["sport"] == "run"
        assert results[1]["period"] == "ytd"
        assert results[1]["sport"] == "ride"
