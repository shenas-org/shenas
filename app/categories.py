"""User-defined categories for classification transforms.

A category groups related labels under a concept (e.g. "Activity Type"
with values Run, Bike, Swim). These feed into the LLM categorize transform
as the valid categories list, and can be managed via the UI.
"""

from __future__ import annotations

import dataclasses
from typing import Annotated

from shenas_plugins.core.table import Field, Table


@dataclasses.dataclass
class CategoryValue(Table):
    """A single value within a category."""

    class _Meta:
        name = "category_values"
        display_name = "Category Values"
        description = "Individual values within a category."
        schema = "shenas_system"
        pk = ("set_id", "value")

    set_id: Annotated[str, Field(db_type="VARCHAR", description="FK to category_sets.id")]
    value: Annotated[str, Field(db_type="VARCHAR", description="The category label")]
    sort_order: Annotated[int, Field(db_type="INTEGER", description="Display order", db_default="0")] = 0
    color: Annotated[str | None, Field(db_type="VARCHAR", description="Optional hex color")] = None


@dataclasses.dataclass
class Category(Table):
    """A named group of category values (e.g. 'Activity Type', 'Expense Category')."""

    class _Meta:
        name = "category_sets"
        display_name = "Category Sets"
        description = "Named groups of categories for classification."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Unique identifier (slug)")]
    display_name: Annotated[str, Field(db_type="VARCHAR", description="Human-readable name")]
    description: Annotated[str, Field(db_type="VARCHAR", description="Optional description", db_default="''")] = ""

    # -- values --

    @property
    def values(self) -> list[CategoryValue]:
        return CategoryValue.all(where="set_id = ?", params=[self.id], order_by="sort_order, value")

    def add_value(self, value: str, sort_order: int = 0, color: str | None = None) -> None:
        CategoryValue(set_id=self.id, value=value, sort_order=sort_order, color=color).insert()

    def remove_value(self, value: str) -> None:
        from app.database import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ? AND value = ?", [self.id, value])

    def replace_values(self, values: list[dict]) -> None:
        """Replace all values with the given list of {value, sortOrder?, color?}."""
        from app.database import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ?", [self.id])
        for i, v in enumerate(values):
            self.add_value(v["value"], sort_order=v.get("sortOrder", i), color=v.get("color"))

    def delete(self) -> None:
        """Delete this category and cascade to its values."""
        from app.database import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ?", [self.id])
        super().delete()
