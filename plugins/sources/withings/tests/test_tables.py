from unittest.mock import MagicMock

from shenas_sources.withings.tables import DailyActivity, Devices, Measurements, SleepSummary


def _make_client() -> MagicMock:
    return MagicMock()


class TestMeasurements:
    def test_extract_yields_flattened_rows(self) -> None:
        client = _make_client()
        client.get_measurements.return_value = [
            {
                "grpid": 1001,
                "created_at": "2026-04-09T08:00:00",
                "weight_kg": 72.5,
                "fat_ratio_pct": 18.2,
                "muscle_mass_kg": 32.1,
            },
        ]
        rows = list(Measurements.extract(client, start_date="7 days ago"))
        assert len(rows) == 1
        assert rows[0]["grpid"] == 1001
        assert rows[0]["weight_kg"] == 72.5
        assert rows[0]["fat_ratio_pct"] == 18.2

    def test_extract_empty(self) -> None:
        client = _make_client()
        client.get_measurements.return_value = []
        assert list(Measurements.extract(client, start_date="7 days ago")) == []


class TestSleepSummary:
    def test_extract_maps_fields(self) -> None:
        client = _make_client()
        client.get_sleep_summary.return_value = [
            {
                "date": "2026-04-08",
                "data": {
                    "total_sleep_duration": 28800,
                    "deepsleepduration": 7200,
                    "remsleepduration": 5400,
                    "lightsleepduration": 14400,
                    "wakeupduration": 1800,
                    "sleep_score": 82,
                },
            },
        ]
        rows = list(SleepSummary.extract(client, start_date="7 days ago"))
        assert len(rows) == 1
        assert rows[0]["date"] == "2026-04-08"
        assert rows[0]["total_sleep_duration_s"] == 28800
        assert rows[0]["deep_sleep_duration_s"] == 7200
        assert rows[0]["sleep_score"] == 82


class TestDailyActivity:
    def test_extract_maps_fields(self) -> None:
        client = _make_client()
        client.get_activity.return_value = [
            {
                "date": "2026-04-08",
                "steps": 8500,
                "distance": 6200.0,
                "calories": 320.5,
                "totalcalories": 2100.0,
                "soft": 3600,
                "moderate": 1800,
                "intense": 600,
            },
        ]
        rows = list(DailyActivity.extract(client, start_date="7 days ago"))
        assert len(rows) == 1
        assert rows[0]["steps"] == 8500
        assert rows[0]["distance_m"] == 6200.0
        assert rows[0]["active_calories_kcal"] == 320.5
        assert rows[0]["intense_activity_duration_s"] == 600


class TestDevices:
    def test_extract_yields_devices(self) -> None:
        client = _make_client()
        client.get_devices.return_value = [
            {
                "deviceid": "dev-001",
                "type": "Scale",
                "model": "Body+",
                "battery": "high",
                "fw": "2.4.6",
            },
        ]
        rows = list(Devices.extract(client))
        assert len(rows) == 1
        assert rows[0]["deviceid"] == "dev-001"
        assert rows[0]["model"] == "Body+"
        assert rows[0]["firmware"] == "2.4.6"

    def test_extract_empty(self) -> None:
        client = _make_client()
        client.get_devices.return_value = []
        assert list(Devices.extract(client)) == []
