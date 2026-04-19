"""End-to-end SCD2 disappearance test for spotify.SavedTracks.

The previous "snapshot" classification of saved_tracks loaded with replace
silently lost history when the user unsaved a track. After migrating to
SnapshotTable (SCD2), unsaving a track should close the row's _dlt_valid_to.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

import shenas_sources.spotify.source  # noqa: F401 -- triggers __init_subclass__
from shenas_sources.spotify.tables import SavedTracks


def _track(track_id: str) -> dict:
    return {
        "added_at": "2026-01-01T00:00:00Z",
        "track": {
            "id": track_id,
            "name": f"Song {track_id}",
            "artists": [{"name": "A"}],
            "album": {"name": "Alb"},
            "duration_ms": 1000,
            "popularity": 50,
        },
    }


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "spotify_saved_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="spotify_saved_scd2",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="sources",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestSavedTracksScd2:
    def test_unsaved_track_closes_row(self, pipeline) -> None:
        client = MagicMock()

        client.current_user_saved_tracks.return_value = {"items": [_track("t1"), _track("t2")]}
        pipeline.run(SavedTracks.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute("SELECT track_id, _dlt_valid_to FROM sources.spotify__saved_tracks ORDER BY track_id").fetchall()
        con.close()
        assert len(rows) == 2
        assert all(r[1] is None for r in rows)

        client.current_user_saved_tracks.return_value = {"items": [_track("t1")]}
        pipeline.run(SavedTracks.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute("SELECT track_id, _dlt_valid_to FROM sources.spotify__saved_tracks ORDER BY track_id").fetchall()
        con.close()

        active = [r for r in rows if r[1] is None]
        closed = [r for r in rows if r[1] is not None]
        assert len(active) == 1
        assert active[0][0] == "t1"
        assert len(closed) == 1
        assert closed[0][0] == "t2", "unsaved track should be SCD2-closed"
