"""End-to-end SCD2 disappearance test for strava.Kudos.

The previous EventTable + merge-on-PK classification of Kudos silently failed
when an athlete revoked a kudo: the link row stayed alive in DuckDB forever.
After migrating to M2MTable (SCD2), removing a kudo should close the row's
``_dlt_valid_to``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

import shenas_sources.strava.source  # noqa: F401 -- triggers __init_subclass__
from shenas_sources.strava.tables import Kudos


def _kudo(athlete_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=athlete_id, firstname=f"User{athlete_id}", lastname="X")


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "strava_kudos_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="strava_kudos_scd2",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="sources",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestKudosScd2:
    def test_kudo_revocation_closes_link(self, pipeline) -> None:
        client = MagicMock()
        # One pre-fetched activity (id=42) is shared via the `detailed` context.
        detailed = [SimpleNamespace(id=42)]

        # Sync 1: activity 42 has kudos from athletes 100 and 200
        client.get_activity_kudos.return_value = [_kudo(100), _kudo(200)]
        pipeline.run(Kudos.to_resource(client, detailed=detailed))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT activity_id, athlete_id, _dlt_valid_to FROM sources.strava__kudos ORDER BY athlete_id"
        ).fetchall()
        con.close()
        assert len(rows) == 2
        assert all(r[2] is None for r in rows), "both kudos should be open after sync 1"

        # Sync 2: athlete 200 revoked their kudo
        client.get_activity_kudos.return_value = [_kudo(100)]
        pipeline.run(Kudos.to_resource(client, detailed=detailed))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT activity_id, athlete_id, _dlt_valid_to FROM sources.strava__kudos ORDER BY athlete_id"
        ).fetchall()
        con.close()

        active = [r for r in rows if r[2] is None]
        closed = [r for r in rows if r[2] is not None]
        assert len(active) == 1
        assert active[0][1] == 100
        assert len(closed) == 1
        assert closed[0][1] == 200, "athlete 200's revoked kudo should be closed by SCD2"
