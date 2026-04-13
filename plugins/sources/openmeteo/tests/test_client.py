"""Tests for the Open-Meteo client helpers."""

from shenas_sources.openmeteo.client import _aggregate_hourly_to_daily, _columnar_to_rows


def test_columnar_to_rows():
    columnar = {
        "time": ["2026-04-01", "2026-04-02"],
        "temperature_2m_max": [10.5, 12.3],
        "precipitation_sum": [0.0, 1.2],
    }
    rows = _columnar_to_rows(columnar)
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-04-01"
    assert rows[0]["temperature_2m_max"] == 10.5
    assert rows[1]["precipitation_sum"] == 1.2


def test_aggregate_hourly_to_daily():
    hourly = {
        "time": [
            "2026-04-01T00:00",
            "2026-04-01T12:00",
            "2026-04-02T06:00",
        ],
        "pm2_5": [10.0, 20.0, 15.0],
        "european_aqi": [30, 50, 40],
    }
    rows = _aggregate_hourly_to_daily(hourly)
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-04-01"
    assert rows[0]["pm2_5"] == 15.0  # mean of 10 and 20
    assert rows[0]["european_aqi"] == 50  # max of 30 and 50
    assert rows[1]["date"] == "2026-04-02"
    assert rows[1]["pm2_5"] == 15.0


def test_aggregate_handles_nulls():
    hourly = {
        "time": ["2026-04-01T00:00", "2026-04-01T12:00"],
        "pm2_5": [None, None],
        "ozone": [40.0, None],
    }
    rows = _aggregate_hourly_to_daily(hourly)
    assert len(rows) == 1
    assert rows[0]["pm2_5"] is None
    assert rows[0]["ozone"] == 40.0
