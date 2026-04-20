"""Tests for the categories module (CategorySet + CategoryValue)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.categories import Category, CategoryValue, create_set, get_set, list_sets

if TYPE_CHECKING:
    import duckdb


@pytest.fixture(autouse=True)
def _ensure_tables(db_con: duckdb.DuckDBPyConnection) -> None:
    """Create the category tables before each test."""
    Category.ensure()
    CategoryValue.ensure()


class TestCreateCategory:
    def test_create_set_with_values(self, db_con) -> None:
        result = create_set("mood", "Mood", description="Daily mood rating")
        assert result["id"] == "mood"
        assert result["displayName"] == "Mood"
        assert result["description"] == "Daily mood rating"
        assert result["values"] == []

        category = Category.find("mood")
        assert category is not None
        category.add_value("great", sort_order=0, color="#00ff00")
        category.add_value("ok", sort_order=1)
        category.add_value("bad", sort_order=2, color="#ff0000")

        values = category.values
        assert len(values) == 3
        assert values[0].value == "great"
        assert values[0].color == "#00ff00"
        assert values[1].value == "ok"
        assert values[2].value == "bad"


class TestGetCategory:
    def test_get_existing_set(self, db_con) -> None:
        create_set("energy", "Energy Level")
        result = get_set("energy")
        assert result is not None
        assert result["id"] == "energy"
        assert result["displayName"] == "Energy Level"

    def test_get_nonexistent_set(self, db_con) -> None:
        result = get_set("nonexistent")
        assert result is None


class TestListCategories:
    def test_list_all_sets(self, db_con) -> None:
        create_set("alpha", "Alpha")
        create_set("beta", "Beta")
        create_set("gamma", "Gamma")

        result = list_sets()
        assert len(result) == 3
        ids = [r["id"] for r in result]
        assert ids == ["alpha", "beta", "gamma"]


class TestUpdateValues:
    def test_replace_values(self, db_con) -> None:
        create_set("stress", "Stress")
        category = Category.find("stress")
        assert category is not None

        category.add_value("low", sort_order=0)
        category.add_value("medium", sort_order=1)
        assert len(category.values) == 2

        category.replace_values(
            [
                {"value": "none", "sortOrder": 0, "color": "#00ff00"},
                {"value": "mild", "sortOrder": 1},
                {"value": "high", "sortOrder": 2, "color": "#ff0000"},
            ]
        )

        values = category.values
        assert len(values) == 3
        assert values[0].value == "none"
        assert values[0].color == "#00ff00"
        assert values[1].value == "mild"
        assert values[1].color is None
        assert values[2].value == "high"

    def test_update_metadata(self, db_con) -> None:
        create_set("focus", "Focus")
        category = Category.find("focus")
        assert category is not None

        category.update_metadata(display_name="Focus Level", description="How focused I am")
        refreshed = Category.find("focus")
        assert refreshed is not None
        assert refreshed.display_name == "Focus Level"
        assert refreshed.description == "How focused I am"


class TestDeleteCategory:
    def test_delete_cascades_to_values(self, db_con) -> None:
        create_set("temp", "Temporary")
        category = Category.find("temp")
        assert category is not None
        category.add_value("a", sort_order=0)
        category.add_value("b", sort_order=1)
        assert len(CategoryValue.all(where="set_id = ?", params=["temp"])) == 2

        category.delete()

        assert Category.find("temp") is None
        assert len(CategoryValue.all(where="set_id = ?", params=["temp"])) == 0
