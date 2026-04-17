"""Tests for DataTable.is_scd2(), scd2_filter(), and auto-filtering in all()."""

from __future__ import annotations

from typing import Annotated

from app.schema import Schema
from app.table import Field
from shenas_sources.core.table import DimensionTable, EventTable


class Dim(DimensionTable):
    class _Meta:
        name = "dim_test"
        display_name = "Dim Test"
        pk = ("id",)
        schema = Schema("test")

    id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


class Evt(EventTable):
    class _Meta:
        name = "evt_test"
        display_name = "Evt Test"
        pk = ("id",)
        schema = Schema("test")
        time_at = "ts"

    id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0
    ts: Annotated[str, Field(db_type="TIMESTAMP", description="ts")] = ""


def test_dimension_is_scd2() -> None:
    assert Dim.is_scd2() is True


def test_event_is_not_scd2() -> None:
    assert Evt.is_scd2() is False


def test_scd2_filter_current() -> None:
    f = Dim.scd2_filter()
    assert f == "_dlt_valid_to IS NULL"


def test_scd2_filter_as_of() -> None:
    f = Dim.scd2_filter(as_of="2025-06-01")
    assert "_dlt_valid_from <= '2025-06-01'" in f
    assert "_dlt_valid_to > '2025-06-01'" in f
    assert "_dlt_valid_to IS NULL" in f


def test_scd2_filter_with_alias() -> None:
    f = Dim.scd2_filter(alias="s")
    assert f == "s._dlt_valid_to IS NULL"


def test_scd2_filter_returns_empty_for_non_scd2() -> None:
    assert Evt.scd2_filter() == ""


def test_all_auto_filters_scd2(db_con) -> None:
    """DataTable.all() for a DimensionTable auto-adds the current-slice filter."""

    db_con.execute("CREATE SCHEMA IF NOT EXISTS test")
    db_con.execute(
        """
        CREATE TABLE test.dim_test (
            id INTEGER,
            value VARCHAR DEFAULT '',
            _dlt_valid_from TIMESTAMP,
            _dlt_valid_to TIMESTAMP
        )
        """
    )
    db_con.execute("INSERT INTO test.dim_test VALUES (1, 'current', '2025-01-01', NULL)")
    db_con.execute("INSERT INTO test.dim_test VALUES (1, 'old', '2024-01-01', '2025-01-01')")

    rows = Dim.all()
    assert len(rows) == 1
    assert rows[0].id == 1


def test_all_include_history_returns_all(db_con) -> None:
    db_con.execute("CREATE SCHEMA IF NOT EXISTS test")
    db_con.execute(
        """
        CREATE TABLE test.dim_test (
            id INTEGER,
            value VARCHAR DEFAULT '',
            _dlt_valid_from TIMESTAMP,
            _dlt_valid_to TIMESTAMP
        )
        """
    )
    db_con.execute("INSERT INTO test.dim_test VALUES (1, 'current', '2025-01-01', NULL)")
    db_con.execute("INSERT INTO test.dim_test VALUES (1, 'old', '2024-01-01', '2025-01-01')")

    rows = Dim.all(include_history=True)
    assert len(rows) == 2
