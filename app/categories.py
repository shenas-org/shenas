"""Category sets -- named groups of values for classification.

Each ``Category`` (a ``CategorySet`` row) has an ordered list of
``CategoryValue`` children. Both are ``Table`` subclasses so they get
automatic CRUD from the table ABC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field, Table


@dataclass
class CategoryValue(Table):
    class _Meta:
        name = "category_values"
        display_name = "Category Values"
        description = "Individual values within a category set."
        schema = "catalog"
        pk = ("set_id", "value")

    set_id: Annotated[str, Field(db_type="VARCHAR", description="Parent category set ID")]
    value: Annotated[str, Field(db_type="VARCHAR", description="The value")]
    sort_order: Annotated[int, Field(db_type="INTEGER", description="Display order", db_default="0")] = 0
    color: Annotated[str | None, Field(db_type="VARCHAR", description="Optional display color")] = None


@dataclass
class Category(Table):
    class _Meta:
        name = "category_sets"
        display_name = "Category Sets"
        description = "Named groups of categories for classification."
        schema = "catalog"
        pk = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Unique identifier (slug)")]
    display_name: Annotated[str, Field(db_type="VARCHAR", description="Human-readable name")]
    description: Annotated[
        str,
        Field(db_type="VARCHAR", description="Optional description", db_default="''"),
    ] = ""

    # -- values --

    @property
    def values(self) -> list[CategoryValue]:
        return CategoryValue.all(where="set_id = ?", params=[self.id], order_by="sort_order, value")

    def add_value(self, value: str, sort_order: int = 0, color: str | None = None) -> None:
        CategoryValue(set_id=self.id, value=value, sort_order=sort_order, color=color).insert()

    def remove_value(self, value: str) -> None:
        cv = CategoryValue.find(self.id, value)
        if cv:
            cv.delete()

    def replace_values(self, values: list[dict]) -> None:
        """Replace all values with the given list of {value, sortOrder?, color?}."""
        for v in self.values:
            v.delete()
        for i, v in enumerate(values):
            self.add_value(v["value"], sort_order=v.get("sortOrder", i), color=v.get("color"))

    def delete(self) -> None:
        """Delete this category and cascade to its values."""
        for v in self.values:
            v.delete()
        super().delete()

    # -- CRUD --

    def update_metadata(self, display_name: str | None = None, description: str | None = None) -> None:
        if display_name is not None:
            self.display_name = display_name
        if description is not None:
            self.description = description
        self.save()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "description": self.description,
            "values": [{"value": v.value, "sortOrder": v.sort_order, "color": v.color} for v in self.values],
        }


# -- Convenience functions (delegate to Category) --


def list_sets() -> list[dict[str, Any]]:
    return [c.to_dict() for c in Category.all(order_by="id")]


def get_set(set_id: str) -> dict[str, Any] | None:
    c = Category.find(set_id)
    return c.to_dict() if c else None


def create_set(set_id: str, display_name: str, description: str = "") -> dict[str, Any]:
    c = Category(id=set_id, display_name=display_name, description=description)
    c.insert()
    return c.to_dict()


# Legacy aliases
CategorySet = Category
