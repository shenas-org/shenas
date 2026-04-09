"""Critical verification: dlt 1.24.0 SCD2 must handle the m2m bridge-table case.

The whole point of M2MTable is that when a link disappears between syncs (the
user removes a tag, unfollows an artist, etc.), dlt's SCD2 loader closes the
row's _dlt_valid_to instead of leaving it alive forever.

If this test fails, the M2MTable design needs a different loader strategy
(probably append-with-observed_at), and we should fall back accordingly.
"""

from __future__ import annotations

from typing import Annotated, Any

import dlt
import duckdb
import pytest

from shenas_plugins.core.table import Field
from shenas_sources.core.table import M2MTable


class TransactionTagsLink(M2MTable):
    """The minimal m2m bridge: composite PK, NO value columns."""

    class _Meta:
        name = "transaction_tags"
        display_name = "Transaction Tags"
        pk = ("transaction_id", "tag_id")

    transaction_id: Annotated[int, Field(db_type="INTEGER", description="Transaction ID")]
    tag_id: Annotated[int, Field(db_type="INTEGER", description="Tag ID")]

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Any:
        yield from client.get_links()


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "m2m_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="m2m_scd2_test",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="test",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestM2MScd2:
    def test_link_appears_then_disappears(self, pipeline) -> None:
        """A link present in sync 1 but missing in sync 2 should have its
        _dlt_valid_to closed by SCD2."""
        from unittest.mock import MagicMock

        client = MagicMock()

        # Sync 1: transaction 42 has tags 100 and 200
        client.get_links.return_value = [
            {"transaction_id": 42, "tag_id": 100},
            {"transaction_id": 42, "tag_id": 200},
        ]
        pipeline.run(TransactionTagsLink.to_resource(client))

        con = _open_db(pipeline)
        rows_after_sync1 = con.execute(
            "SELECT transaction_id, tag_id, _dlt_valid_from, _dlt_valid_to FROM test.transaction_tags ORDER BY tag_id"
        ).fetchall()
        con.close()
        assert len(rows_after_sync1) == 2
        assert all(r[3] is None for r in rows_after_sync1), "both versions should be active after sync 1"

        # Sync 2: tag 200 is removed; tag 100 remains
        client.get_links.return_value = [
            {"transaction_id": 42, "tag_id": 100},
        ]
        pipeline.run(TransactionTagsLink.to_resource(client))

        con = _open_db(pipeline)
        rows_after_sync2 = con.execute(
            "SELECT transaction_id, tag_id, _dlt_valid_from, _dlt_valid_to FROM test.transaction_tags ORDER BY tag_id"
        ).fetchall()
        con.close()

        # We expect 2 total rows: tag 100 still active, tag 200 closed.
        active = [r for r in rows_after_sync2 if r[3] is None]
        closed = [r for r in rows_after_sync2 if r[3] is not None]
        assert len(active) == 1
        assert active[0][1] == 100
        assert len(closed) == 1, (
            "tag 200 should have been closed by SCD2 disappearance detection. "
            f"got {len(closed)} closed rows total: {rows_after_sync2}"
        )
        assert closed[0][1] == 200

    def test_repeated_identical_syncs_do_not_mint_new_versions(self, pipeline) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_links.return_value = [
            {"transaction_id": 1, "tag_id": 100},
            {"transaction_id": 1, "tag_id": 200},
        ]
        pipeline.run(TransactionTagsLink.to_resource(client))
        pipeline.run(TransactionTagsLink.to_resource(client))
        pipeline.run(TransactionTagsLink.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute("SELECT transaction_id, tag_id FROM test.transaction_tags").fetchall()
        con.close()
        assert len(rows) == 2  # not 6 -- SCD2 dedupes
