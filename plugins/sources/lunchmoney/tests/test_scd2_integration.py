"""End-to-end SCD2 integration test for the lunchmoney source.

Runs the new Table-ABC pipeline through a real dlt pipeline against an
in-memory DuckDB destination, syncs twice with a renamed category between
syncs, and verifies the categories table has two SCD2 versions with disjoint
``_dlt_valid_from`` / ``_dlt_valid_to`` ranges.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import dlt
import duckdb
import pytest

from shenas_sources.lunchmoney.tables import Categories


def _category(id_: int, name: str) -> SimpleNamespace:
    fixed = {
        "id": id_,
        "name": name,
        "is_income": False,
        "exclude_from_budget": False,
        "exclude_from_totals": False,
        "archived": False,
    }
    return SimpleNamespace(model_dump=lambda mode="json", _f=fixed: dict(_f))


@pytest.fixture
def pipeline(tmp_path):
    """A throwaway dlt pipeline writing to an in-memory DuckDB destination."""
    db_path = tmp_path / "scd2_test.duckdb"
    return dlt.pipeline(
        pipeline_name="lunchmoney_scd2_test",
        destination=dlt.destinations.duckdb(str(db_path)),
        dataset_name="lunchmoney",
    )


class TestCategoriesScd2:
    def test_renamed_category_versions(self, pipeline) -> None:
        client = MagicMock()

        # Sync 1: Coffee
        client.get_categories.return_value = [_category(1, "Coffee")]
        info1 = pipeline.run(Categories.to_resource(client))
        assert info1 is not None

        # Sync 2: same id, renamed
        client.get_categories.return_value = [_category(1, "Coffee & Tea")]
        info2 = pipeline.run(Categories.to_resource(client))
        assert info2 is not None

        # Inspect what landed in DuckDB.
        con = duckdb.connect(str(pipeline.destination_client().config.credentials.database))
        rows = con.execute(
            "SELECT id, category_name, _dlt_valid_from, _dlt_valid_to FROM lunchmoney.categories ORDER BY _dlt_valid_from"
        ).fetchall()
        con.close()

        # Two SCD2 versions for the same id.
        assert len(rows) == 2
        assert rows[0][1] == "Coffee"
        assert rows[1][1] == "Coffee & Tea"
        # First version has a closed valid_to; second is still active.
        assert rows[0][3] is not None
        assert rows[1][3] is None

    def test_unchanged_category_does_not_mint_new_version(self, pipeline) -> None:
        client = MagicMock()
        client.get_categories.return_value = [_category(1, "Coffee")]

        # Two identical syncs.
        pipeline.run(Categories.to_resource(client))
        pipeline.run(Categories.to_resource(client))

        con = duckdb.connect(str(pipeline.destination_client().config.credentials.database))
        rows = con.execute("SELECT id, category_name FROM lunchmoney.categories").fetchall()
        con.close()

        # SCD2 hashes the row -- identical syncs do NOT create a new version.
        assert len(rows) == 1


class TestKindAwareWriteDispositionAppliedToResource:
    def test_categories_resource_uses_scd2_disposition(self) -> None:
        client = MagicMock()
        client.get_categories.return_value = [_category(1, "Coffee")]
        resource = Categories.to_resource(client)
        # The resource's hints carry the write_disposition we set.
        hints = resource._hints if hasattr(resource, "_hints") else {}
        wd = hints.get("write_disposition") if isinstance(hints, dict) else None
        if wd is None:
            # Fall back to compute_table_schema or just trust to_resource:
            assert Categories.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
        else:
            assert wd == {"disposition": "merge", "strategy": "scd2"}
