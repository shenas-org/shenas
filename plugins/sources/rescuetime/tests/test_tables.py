"""Tests for RescueTime source tables."""

from __future__ import annotations

from shenas_sources.rescuetime.tables import Activities, DailySummary


class FakeClient:
    """Stub that returns canned API responses."""

    def get_daily_summary(self):
        return [
            {
                "date": "2024-01-15",
                "productivity_pulse": 72.0,
                "total_hours": 8.5,
                "very_productive_hours": 3.84,
                "productive_hours": 1.71,
                "neutral_hours": 1.30,
                "distracting_hours": 0.89,
                "very_distracting_hours": 0.76,
            }
        ]

    def get_activities(self, start_date: str, end_date: str):
        return [
            ["2024-01-15", 3600, 1, "Visual Studio Code", "Editing & IDEs", 2],
            ["2024-01-15", 1800, 1, "github.com", "General Software Development", 2],
            ["2024-01-15", 900, 1, "reddit.com", "General News & Opinion", -2],
        ]


def test_daily_summary_extract() -> None:
    rows = list(DailySummary.extract(FakeClient()))
    assert len(rows) == 1

    row = rows[0]
    assert row["date"] == "2024-01-15"
    assert row["productivity_pulse"] == 72.0
    assert row["total_s"] == 30600.0  # 8.5 * 3600
    assert row["very_productive_s"] == 13824.0  # 3.84 * 3600


def test_activities_extract() -> None:
    rows = list(Activities.extract(FakeClient(), start_date="30 days ago"))
    assert len(rows) == 3

    assert rows[0]["activity"] == "Visual Studio Code"
    assert rows[0]["category"] == "Editing & IDEs"
    assert rows[0]["duration_s"] == 3600.0
    assert rows[0]["productivity"] == 2

    assert rows[2]["activity"] == "reddit.com"
    assert rows[2]["productivity"] == -2
