"""User-defined category sets for classification transforms.

A category set groups related labels under a concept (e.g. "Activity Type"
with values Run, Bike, Swim). These feed into the LLM categorize transform
as the valid categories list, and can be managed via the UI.
"""

from __future__ import annotations

import dataclasses
from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table


@dataclasses.dataclass
class CategorySet(Table):
    """A named group of categories (e.g. 'Activity Type', 'Expense Category')."""

    class _Meta:
        name = "category_sets"
        display_name = "Category Sets"
        description = "Named groups of categories for classification."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Unique identifier (slug)")]
    display_name: Annotated[str, Field(db_type="VARCHAR", description="Human-readable name")]
    description: Annotated[str, Field(db_type="VARCHAR", description="Optional description", db_default="''")] = ""


@dataclasses.dataclass
class CategoryValue(Table):
    """A single value within a category set."""

    class _Meta:
        name = "category_values"
        display_name = "Category Values"
        description = "Individual values within a category set."
        schema = "shenas_system"
        pk = ("set_id", "value")

    set_id: Annotated[str, Field(db_type="VARCHAR", description="FK to category_sets.id")]
    value: Annotated[str, Field(db_type="VARCHAR", description="The category label")]
    sort_order: Annotated[int, Field(db_type="INTEGER", description="Display order", db_default="0")] = 0
    color: Annotated[str | None, Field(db_type="VARCHAR", description="Optional hex color")] = None


def list_sets() -> list[dict[str, Any]]:
    """Return all category sets with their values."""
    sets = CategorySet.all(order_by="display_name")
    result = []
    for s in sets:
        values = CategoryValue.all(where="set_id = ?", params=[s.id], order_by="sort_order, value")
        result.append(
            {
                "id": s.id,
                "displayName": s.display_name,
                "description": s.description,
                "values": [{"value": v.value, "sortOrder": v.sort_order, "color": v.color} for v in values],
            }
        )
    return result


def get_set(set_id: str) -> dict[str, Any] | None:
    """Return a single category set with values."""
    s = CategorySet.find(set_id)
    if not s:
        return None
    values = CategoryValue.all(where="set_id = ?", params=[s.id], order_by="sort_order, value")
    return {
        "id": s.id,
        "displayName": s.display_name,
        "description": s.description,
        "values": [{"value": v.value, "sortOrder": v.sort_order, "color": v.color} for v in values],
    }


def create_set(set_id: str, display_name: str, description: str = "", values: list[dict] | None = None) -> dict[str, Any]:
    """Create a new category set with optional initial values."""
    s = CategorySet(id=set_id, display_name=display_name, description=description)
    s.insert()
    if values:
        for i, v in enumerate(values):
            cv = CategoryValue(set_id=set_id, value=v["value"], sort_order=v.get("sortOrder", i), color=v.get("color"))
            cv.insert()
    return get_set(set_id)  # type: ignore[return-value]


def update_set(set_id: str, display_name: str | None = None, description: str | None = None) -> dict[str, Any] | None:
    """Update a category set's metadata."""
    s = CategorySet.find(set_id)
    if not s:
        return None
    if display_name is not None:
        s.display_name = display_name
    if description is not None:
        s.description = description
    s.save()
    return get_set(set_id)


def delete_set(set_id: str) -> bool:
    """Delete a category set and all its values."""
    s = CategorySet.find(set_id)
    if not s:
        return False
    from app.db import cursor

    with cursor() as cur:
        cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ?", [set_id])
    s.delete()
    return True


def add_value(set_id: str, value: str, sort_order: int = 0, color: str | None = None) -> dict[str, Any] | None:
    """Add a value to a category set."""
    if not CategorySet.find(set_id):
        return None
    cv = CategoryValue(set_id=set_id, value=value, sort_order=sort_order, color=color)
    cv.insert()
    return get_set(set_id)


def remove_value(set_id: str, value: str) -> dict[str, Any] | None:
    """Remove a value from a category set."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ? AND value = ?", [set_id, value])
    return get_set(set_id)


def update_values(set_id: str, values: list[dict]) -> dict[str, Any] | None:
    """Replace all values in a category set."""
    if not CategorySet.find(set_id):
        return None
    from app.db import cursor

    with cursor() as cur:
        cur.execute("DELETE FROM shenas_system.category_values WHERE set_id = ?", [set_id])
    for i, v in enumerate(values):
        cv = CategoryValue(set_id=set_id, value=v["value"], sort_order=v.get("sortOrder", i), color=v.get("color"))
        cv.insert()
    return get_set(set_id)
