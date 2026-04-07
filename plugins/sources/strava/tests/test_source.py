"""Tests for Strava source tables (Table ABC pattern)."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from shenas_sources.strava.tables import (
    Activities,
    Athlete,
    AthleteStats,
    AthleteZones,
    Comments,
    Gear,
    Kudos,
    Laps,
    fetch_detailed_activities,
)

_activity_row = Activities._activity_row


def _make_activity(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 12345,
        "name": "Morning Run",
        "description": "felt good",
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
        "average_temp": 14.0,
        "kilojoules": None,
        "calories": 320.5,
        "average_watts": None,
        "max_watts": None,
        "suffer_score": 25.0,
        "achievement_count": 2,
        "kudos_count": 5,
        "comment_count": 1,
        "total_photo_count": 0,
        "gear_id": "g1",
        "device_name": "Garmin",
        "trainer": False,
        "commute": False,
        "manual": False,
        "laps": [],
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
        assert row["kudos_count"] == 5
        assert row["comment_count"] == 1
        assert row["achievement_count"] == 2
        assert row["gear_id"] == "g1"

    def test_handles_missing_fields(self) -> None:
        a = _make_activity(calories=None, average_watts=None, max_watts=None)
        row = _activity_row(a)
        assert row["calories"] is None
        assert row["average_watts"] is None
        assert row["max_watts"] is None

    def test_plain_numeric_values(self) -> None:
        a = _make_activity(average_heartrate=148, max_heartrate=170)
        row = _activity_row(a)
        assert row["average_heartrate"] == 148.0
        assert row["max_heartrate"] == 170.0

    def test_end_date_computed_from_start_plus_elapsed(self) -> None:
        row = _activity_row(_make_activity())
        # 2026-03-28T08:00:00 + 1850 seconds = 08:30:50
        assert row["end_date"] is not None
        assert row["end_date"].startswith("2026-03-28T08:30:50")

    def test_end_date_none_when_start_or_elapsed_missing(self) -> None:
        row = _activity_row(_make_activity(start_date=None))
        assert row["end_date"] is None
        row = _activity_row(_make_activity(elapsed_time=None))
        assert row["end_date"] is None


class TestFetchDetailedActivities:
    def test_calls_get_activity_per_summary(self) -> None:
        client = MagicMock()
        client.get_activities.return_value = iter([SimpleNamespace(id=1), SimpleNamespace(id=2)])
        client.get_activity.side_effect = lambda i, include_all_efforts=False: _make_activity(id=i)

        result = fetch_detailed_activities(client, start_date="2026-03-01")
        assert len(result) == 2
        assert client.get_activity.call_count == 2
        assert [a.id for a in result] == [1, 2]


class TestActivitiesAndLapsExtract:
    def test_activities_yields_rows(self) -> None:
        detailed = [_make_activity(id=1), _make_activity(id=2, name="Ride")]
        rows = list(Activities.extract(MagicMock(), detailed=detailed))
        assert [r["id"] for r in rows] == [1, 2]

    def test_laps_yields_per_lap(self) -> None:
        lap1 = SimpleNamespace(
            id=10,
            lap_index=1,
            name="Lap 1",
            start_date=datetime(2026, 3, 28, 8, 0, tzinfo=UTC),
            distance=SimpleNamespace(magnitude=1000.0),
            moving_time=SimpleNamespace(magnitude=300),
            elapsed_time=SimpleNamespace(magnitude=310),
            total_elevation_gain=SimpleNamespace(magnitude=5.0),
            average_speed=SimpleNamespace(magnitude=3.3),
            max_speed=SimpleNamespace(magnitude=4.0),
            average_heartrate=145.0,
            max_heartrate=160.0,
            average_watts=None,
            average_cadence=85.0,
        )
        lap2 = SimpleNamespace(**{**lap1.__dict__, "id": 11, "lap_index": 2})
        detailed = [_make_activity(id=999, laps=[lap1, lap2])]
        rows = list(Laps.extract(MagicMock(), detailed=detailed))
        assert len(rows) == 2
        assert rows[0]["activity_id"] == 999
        assert rows[0]["lap_index"] == 1
        assert rows[0]["distance_m"] == 1000.0
        # Lap end_date is computed from start + elapsed_time
        assert rows[0]["end_date"] is not None
        assert rows[0]["end_date"].startswith("2026-03-28T08:05:10")


class TestKudosM2M:
    def test_yields_link_rows_only(self) -> None:
        client = MagicMock()
        client.get_activity_kudos.return_value = [
            SimpleNamespace(id=100, firstname="Alice", lastname="A"),
            SimpleNamespace(id=101, firstname="Bob", lastname="B"),
        ]
        detailed = [_make_activity(id=42)]
        rows = list(Kudos.extract(client, detailed=detailed))
        # Pure m2m link -- only the FKs, no firstname/lastname.
        assert sorted((r["activity_id"], r["athlete_id"]) for r in rows) == [(42, 100), (42, 101)]
        for row in rows:
            assert set(row.keys()) == {"activity_id", "athlete_id"}

    def test_kind_is_m2m_relation_with_scd2(self) -> None:
        assert Kudos.kind == "m2m_relation"
        assert Kudos.write_disposition() == {"disposition": "merge", "strategy": "scd2"}


class TestCommentsExtract:
    def test_yields_comment_rows(self) -> None:
        client = MagicMock()
        client.get_activity_comments.return_value = [
            SimpleNamespace(
                id=200,
                text="nice",
                created_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC),
                athlete=SimpleNamespace(id=300, firstname="Carol", lastname="C"),
            )
        ]
        detailed = [_make_activity(id=42)]
        rows = list(Comments.extract(client, detailed=detailed))
        assert len(rows) == 1
        assert rows[0]["athlete_name"] == "Carol C"
        assert rows[0]["text"] == "nice"


class TestSnapshotExtract:
    def test_athlete(self) -> None:
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
        rows = list(Athlete.extract(client))
        assert rows[0]["weight_kg"] == 72.5
        assert rows[0]["ftp"] == 240

    def test_athlete_stats(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = SimpleNamespace(id=999)
        stats = SimpleNamespace(
            biggest_ride_distance=SimpleNamespace(magnitude=120000.0),
            biggest_climb_elevation_gain=SimpleNamespace(magnitude=850.0),
            recent_run_totals=SimpleNamespace(count=4, distance=SimpleNamespace(magnitude=42000.0), moving_time=14400),
            recent_ride_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
            recent_swim_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
            ytd_run_totals=SimpleNamespace(count=12, distance=SimpleNamespace(magnitude=126000.0), moving_time=43200),
            ytd_ride_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
            ytd_swim_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
            all_run_totals=SimpleNamespace(count=200, distance=SimpleNamespace(magnitude=2000000.0), moving_time=720000),
            all_ride_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
            all_swim_totals=SimpleNamespace(count=0, distance=None, moving_time=None),
        )
        client.get_athlete_stats.return_value = stats
        rows = list(AthleteStats.extract(client))
        assert rows[0]["athlete_id"] == 999
        assert rows[0]["biggest_ride_distance_m"] == 120000.0
        assert rows[0]["recent_run_count"] == 4
        assert rows[0]["all_run_count"] == 200

    def test_athlete_zones(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = SimpleNamespace(id=999)
        client.get_athlete_zones.return_value = SimpleNamespace(
            heart_rate=SimpleNamespace(
                zones=[SimpleNamespace(min=0, max=120), SimpleNamespace(min=120, max=140)],
            ),
            power=None,
        )
        rows = list(AthleteZones.extract(client))
        assert len(rows) == 1
        hr = json.loads(rows[0]["heart_rate_zones"])
        assert hr == [{"min": 0, "max": 120}, {"min": 120, "max": 140}]
        assert rows[0]["power_zones"] is None

    def test_athlete_zones_handles_missing(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = SimpleNamespace(id=999)
        client.get_athlete_zones.side_effect = RuntimeError("no zones")
        rows = list(AthleteZones.extract(client))
        assert rows == []


class TestGearCounter:
    def test_yields_bikes_and_shoes(self) -> None:
        client = MagicMock()
        client.get_athlete.return_value = SimpleNamespace(
            bikes=[SimpleNamespace(id="b1", name="Road", primary=True, distance=SimpleNamespace(magnitude=8000.0))],
            shoes=[SimpleNamespace(id="g1", name="Trainers", primary=True, distance=SimpleNamespace(magnitude=400.0))],
        )
        client.get_gear.side_effect = lambda gid: SimpleNamespace(
            id=gid,
            name=f"detail-{gid}",
            brand_name="Acme",
            model_name="X",
            distance=SimpleNamespace(magnitude=8000.0 if gid == "b1" else 400.0),
            primary=True,
            retired=False,
        )
        rows = list(Gear.extract(client))
        assert len(rows) == 2
        types = {r["type"] for r in rows}
        assert types == {"bike", "shoe"}
        bike = next(r for r in rows if r["type"] == "bike")
        assert bike["brand_name"] == "Acme"
        assert bike["distance_m"] == 8000.0

    def test_kind_is_counter_with_append(self) -> None:
        assert Gear.kind == "counter"
        assert Gear.write_disposition() == "append"

    def test_observed_at_auto_injected(self) -> None:
        # Counter tables get observed_at injected so consumers can compute deltas.
        cols = Gear.to_dlt_columns()
        assert "observed_at" in cols


class TestKindsAndDispositions:
    def test_activities_is_interval(self) -> None:
        assert Activities.kind == "interval"
        assert Activities.write_disposition() == "merge"
        assert Activities.time_start == "start_date"
        assert Activities.time_end == "end_date"

    def test_laps_is_interval(self) -> None:
        assert Laps.kind == "interval"
        assert Laps.time_start == "start_date"
        assert Laps.time_end == "end_date"

    def test_comments_is_event(self) -> None:
        assert Comments.kind == "event"
        assert Comments.time_at == "created_at"

    def test_athlete_is_snapshot_scd2(self) -> None:
        assert Athlete.kind == "snapshot"
        assert Athlete.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
