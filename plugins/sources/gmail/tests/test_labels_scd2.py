"""End-to-end SCD2 history test for gmail.Labels.

Previously labels were loaded with replace, so renaming or deleting a
label silently rewrote every historical join. After migrating to
DimensionTable (SCD2), the rename mints a new version and the old name
stays addressable via _dlt_valid_from / _dlt_valid_to.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

import shenas_sources.gmail.source  # noqa: F401 -- triggers __init_subclass__
from shenas_sources.gmail.tables import Labels


def _label(label_id: str, name: str) -> dict:
    return {"id": label_id, "name": name, "type": "user"}


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "gmail_labels_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="gmail_labels_scd2",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="sources",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestLabelsScd2:
    def test_rename_versions_via_scd2(self, pipeline) -> None:
        client = MagicMock()

        client.users().labels().list().execute.return_value = {"labels": [_label("L1", "Work")]}
        pipeline.run(Labels.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT id, label_name, _dlt_valid_to FROM sources.gmail__labels ORDER BY _dlt_valid_from"
        ).fetchall()
        con.close()
        assert len(rows) == 1
        assert rows[0][1] == "Work"
        assert rows[0][2] is None

        client.users().labels().list().execute.return_value = {"labels": [_label("L1", "Day Job")]}
        pipeline.run(Labels.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT id, label_name, _dlt_valid_to FROM sources.gmail__labels ORDER BY _dlt_valid_from"
        ).fetchall()
        con.close()

        assert len(rows) == 2
        assert rows[0][1] == "Work"
        assert rows[0][2] is not None, "old label name should be SCD2-closed"
        assert rows[1][1] == "Day Job"
        assert rows[1][2] is None
