"""End-to-end SCD2 disappearance test for duolingo.Friends.

Previously friends were loaded with replace, so unfollowing silently
erased history. After migrating to SnapshotTable (SCD2), unfollowing
closes the row's _dlt_valid_to.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

from shenas_sources.duolingo.tables import Friends


def _friend(uid: int, username: str) -> dict:
    return {"userId": uid, "username": username, "displayName": username.title(), "totalXp": 1000, "streak": 1}


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "duolingo_friends_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="duolingo_friends_scd2",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="duolingo",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestFriendsScd2:
    def test_unfollow_closes_row(self, pipeline) -> None:
        client = MagicMock()
        client.get_followers.return_value = []

        client.get_following.return_value = [_friend(1, "alice"), _friend(2, "bob")]
        pipeline.run(Friends.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute("SELECT user_id, _dlt_valid_to FROM duolingo.friends ORDER BY user_id").fetchall()
        con.close()
        assert len(rows) == 2
        assert all(r[1] is None for r in rows)

        client.get_following.return_value = [_friend(1, "alice")]
        pipeline.run(Friends.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute("SELECT user_id, _dlt_valid_to FROM duolingo.friends ORDER BY user_id").fetchall()
        con.close()

        active = [r for r in rows if r[1] is None]
        closed = [r for r in rows if r[1] is not None]
        assert len(active) == 1
        assert active[0][0] == 1
        assert len(closed) == 1
        assert closed[0][0] == 2, "unfollowed user should be SCD2-closed"
