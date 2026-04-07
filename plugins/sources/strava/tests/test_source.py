"""Tests for Strava source resources."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from shenas_sources.strava.resources import _activity_row, activities, athlete


def _make_activity(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 12345,
        "name": "Morning Run",
        "sport_type": "Run",
        "start_date": datetime(2026, 3, 28, 8, 0, tzinfo=UTC),
        "timezone": "(GMT+01:00) Europe/Stockholm",
        "distance": SimpleNamespace(magnitude=5000.0),
        "moving_time": SimpleNamespace(magnitude=1800),
        "elapsed_time": SimpleNamespace(magnitude=1850),
        "total_elevation_gain": SimpleNamespace(magnitude=42.0),
        "average_speed": SimpleNamespace(magnitude=2.78),
        "max_speed": SimpleNamespace(magnitude=4.1),
        "average_heartrate": 150.0,
        "max_heartrate": 175.0,
        "kilojoules": None,
        "calories": 320.5,
        "average_watts": None,
        "max_watts": None,
        "suffer_score": 25.0,
        "trainer": False,
        "commute": False,
        "manual": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestActivityRow:
    def test_unwraps_pint_quantities(self) -> None:
        row = _activity_row(_make_activity())
        assert row["id"] == 12345
        assert row["sport_type"] == "Run"
        assert row["distance_m"] == 5000.0
        assert row["moving_time_s"] == 1800
        assert row["elevation_gain_m"] == 42.0
        assert row["calories"] == 320.5
        assert row["start_date"] == "2026-03-28T08:00:00+00:00"

    def test_handles_missing_fields(self) -> None:
        activity = _make_activity(calories=None, average_watts=None, max_watts=None)
        row = _activity_row(activity)
        assert row["calories"] is None
        assert row["average_watts"] is None
        assert row["max_watts"] is None

    def test_plain_numeric_values(self) -> None:
        # Some stravalib fields aren't pint quantities -- e.g. average_heartrate.
        activity = _make_activity(average_heartrate=148, max_heartrate=170)
        row = _activity_row(activity)
        assert row["average_heartrate"] == 148.0
        assert row["max_heartrate"] == 170.0


class TestActivitiesResource:
    def test_yields_rows_from_client(self) -> None:
        client = MagicMock()
        client.get_activities.return_value = iter([_make_activity(), _make_activity(id=2, name="Ride")])

        rows = list(activities(client, start_date="2026-03-01"))
        assert len(rows) == 2
        assert rows[0]["id"] == 12345
        assert rows[1]["id"] == 2
        assert rows[1]["name"] == "Ride"


class TestAthleteResource:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = SimpleNamespace(
            id=999,
            username="testuser",
            firstname="Test",
            lastname="User",
            city="Stockholm",
            country="Sweden",
            sex="M",
            weight=SimpleNamespace(magnitude=72.5),
            ftp=240,
        )

        rows = list(athlete(client))
        assert len(rows) == 1
        assert rows[0]["id"] == 999
        assert rows[0]["weight_kg"] == 72.5
        assert rows[0]["ftp"] == 240
