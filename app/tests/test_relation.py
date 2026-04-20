"""Tests for Relation base class: all(), find(), from_row(), distinct_values()."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import pytest

from app.relation import Field
from app.schema import Schema
from app.table import Table

if TYPE_CHECKING:
    import duckdb

_TEST_SCHEMA = Schema("test_relation")


@dataclass
class _TestItem(Table):
    class _Meta:
        name = "test_items"
        display_name = "Test Items"
        pk = ("id",)
        schema = _TEST_SCHEMA
        database = "shenas"

    id: Annotated[int, Field(db_type="INTEGER", description="primary key")] = 0
    name: Annotated[str, Field(db_type="VARCHAR", description="item name")] = ""
    category: Annotated[str | None, Field(db_type="VARCHAR", description="optional category")] = None


@pytest.fixture(autouse=True)
def _setup_table(db_con: duckdb.DuckDBPyConnection) -> None:
    """Create the test table before each test."""
    _TestItem.ensure()


def _insert_sample_rows() -> None:
    """Insert a handful of rows for testing."""
    _TestItem(id=1, name="apple", category="fruit").insert()
    _TestItem(id=2, name="banana", category="fruit").insert()
    _TestItem(id=3, name="carrot", category="vegetable").insert()
    _TestItem(id=4, name="unknown", category=None).insert()


# ------------------------------------------------------------------
# distinct_values
# ------------------------------------------------------------------


class TestDistinctValues:
    def test_returns_unique_non_null_values(self) -> None:
        _insert_sample_rows()
        values = _TestItem.distinct_values("category")
        # NULLs are excluded (filtered by WHERE column IS NOT NULL)
        assert set(values) == {"fruit", "vegetable"}

    def test_returns_unique_non_null_for_non_null_column(self) -> None:
        _insert_sample_rows()
        values = _TestItem.distinct_values("name")
        assert set(values) == {"apple", "banana", "carrot", "unknown"}

    def test_with_where_filter(self) -> None:
        _insert_sample_rows()
        values = _TestItem.distinct_values("name", where="category = ?", params=["fruit"])
        assert set(values) == {"apple", "banana"}

    def test_empty_table_returns_empty_list(self) -> None:
        values = _TestItem.distinct_values("category")
        assert values == []


# ------------------------------------------------------------------
# all()
# ------------------------------------------------------------------


class TestAll:
    def test_with_where_and_params(self) -> None:
        _insert_sample_rows()
        items = _TestItem.all(where="category = ?", params=["vegetable"])
        assert len(items) == 1
        assert items[0].name == "carrot"

    def test_with_order_by(self) -> None:
        _insert_sample_rows()
        items = _TestItem.all(order_by="name ASC")
        names = [item.name for item in items]
        assert names == ["apple", "banana", "carrot", "unknown"]

    def test_with_limit(self) -> None:
        _insert_sample_rows()
        items = _TestItem.all(order_by="id ASC", limit=2)
        assert len(items) == 2
        assert items[0].id == 1
        assert items[1].id == 2


# ------------------------------------------------------------------
# find()
# ------------------------------------------------------------------


class TestFind:
    def test_returns_none_for_missing_pk(self) -> None:
        _insert_sample_rows()
        result = _TestItem.find(999)
        assert result is None

    def test_returns_instance_for_existing_pk(self) -> None:
        _insert_sample_rows()
        result = _TestItem.find(2)
        assert result is not None
        assert result.name == "banana"
        assert result.category == "fruit"


# ------------------------------------------------------------------
# from_row()
# ------------------------------------------------------------------


class TestFromRow:
    def test_constructs_from_tuple(self) -> None:
        item = _TestItem.from_row((42, "melon", "fruit"))
        assert item.id == 42
        assert item.name == "melon"
        assert item.category == "fruit"

    def test_constructs_with_none_field(self) -> None:
        item = _TestItem.from_row((7, "mystery", None))
        assert item.id == 7
        assert item.name == "mystery"
        assert item.category is None
