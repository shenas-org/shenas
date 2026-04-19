"""End-to-end SCD2 history test for gcalendar.Calendars.

Previously calendars were loaded with replace, so renaming a calendar
silently rewrote every historical join. After migrating to DimensionTable
(SCD2), the rename mints a new version and the old name stays addressable
via _dlt_valid_from / _dlt_valid_to.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

import shenas_sources.gcalendar.source  # noqa: F401 -- triggers __init_subclass__ to prefix table names
from shenas_sources.gcalendar.tables import Calendars


def _calendar(cal_id: str, summary: str) -> dict:
    return {
        "id": cal_id,
        "summary": summary,
        "primary": False,
        "accessRole": "owner",
        "timeZone": "Europe/Stockholm",
    }


@pytest.fixture
def pipeline(tmp_path):
    db_path = tmp_path / "gcal_calendars_scd2.duckdb"
    return dlt.pipeline(
        pipeline_name="gcal_calendars_scd2",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="sources",
    )


def _open_db(pipeline) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(pipeline.destination_client().config.credentials.database))


class TestCalendarsScd2:
    def test_rename_versions_via_scd2(self, pipeline) -> None:
        client = MagicMock()

        client.calendarList().list().execute.return_value = {"items": [_calendar("c1", "Work")]}
        pipeline.run(Calendars.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT id, summary, _dlt_valid_to FROM sources.gcalendar__calendars ORDER BY _dlt_valid_from"
        ).fetchall()
        con.close()
        assert len(rows) == 1
        assert rows[0][1] == "Work"
        assert rows[0][2] is None

        client.calendarList().list().execute.return_value = {"items": [_calendar("c1", "Day Job")]}
        pipeline.run(Calendars.to_resource(client))

        con = _open_db(pipeline)
        rows = con.execute(
            "SELECT id, summary, _dlt_valid_to FROM sources.gcalendar__calendars ORDER BY _dlt_valid_from"
        ).fetchall()
        con.close()

        assert len(rows) == 2
        assert rows[0][1] == "Work"
        assert rows[0][2] is not None, "old name should be SCD2-closed"
        assert rows[1][1] == "Day Job"
        assert rows[1][2] is None
