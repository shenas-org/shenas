"""Cronometer source tables.

Parses Cronometer CSV exports. Column headers like ``Energy (kcal)`` are
normalised to ``energy_kcal``. Only the key macro columns are declared
explicitly -- dlt picks up all remaining nutrient columns dynamically,
just like Obsidian's frontmatter tables.

Expected CSV files in the export directory:

- ``dailySummary.csv`` (or any file containing "daily" in its name)
- ``servings.csv`` (or any file containing "serving" in its name)
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field
from shenas_sources.core.table import AggregateTable, EventTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Greek mu and micro sign to ASCII
_UNIT_ALIASES: dict[str, str] = {"\u00b5": "u", "\u03bc": "u"}


def _normalize_header(header: str) -> str:
    """``Energy (kcal)`` -> ``energy_kcal``, ``Vitamin A (ug)`` -> ``vitamin_a_ug``."""
    result = header.strip()
    for orig, repl in _UNIT_ALIASES.items():
        result = result.replace(orig, repl)
    # Pull parenthetical unit out: "Energy (kcal)" -> "Energy_kcal"
    result = re.sub(r"\s*\(([^)]+)\)\s*", r"_\1", result)
    result = result.replace(" ", "_").replace("-", "_")
    return re.sub(r"_+", "_", result.lower()).strip("_")


def _try_float(value: str) -> float | str | None:
    """Try to parse as float, otherwise return the string (or None if empty)."""
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return v


def _find_csv(export_dir: str, *keywords: str) -> Path | None:
    """Find a CSV file in the export directory matching any of the keywords."""
    d = Path(export_dir)
    for f in sorted(d.glob("*.csv")):
        name_lower = f.stem.lower()
        if any(kw in name_lower for kw in keywords):
            return f
    return None


def _read_csv(path: Path) -> Iterator[dict[str, Any]]:
    """Read a CSV file and yield rows with normalised column names."""
    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield {_normalize_header(k): _try_float(v) if k != "Date" else v for k, v in row.items() if k}


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class DailyNutrition(AggregateTable):
    """Daily nutrient totals from Cronometer's Daily Nutrition export.

    Only the main macronutrient columns are declared -- all remaining
    micronutrient columns are loaded dynamically by dlt.
    """

    class _Meta:
        name = "daily_nutrition"
        display_name = "Daily Nutrition"
        description = "Daily macro- and micronutrient totals from Cronometer."
        pk = ("date",)

    time_at: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""
    energy_kcal: Annotated[float | None, Field(db_type="DOUBLE", description="Total energy", unit="kcal")] = None
    protein_g: Annotated[float | None, Field(db_type="DOUBLE", description="Total protein", unit="g")] = None
    carbs_g: Annotated[float | None, Field(db_type="DOUBLE", description="Total carbohydrates", unit="g")] = None
    fat_g: Annotated[float | None, Field(db_type="DOUBLE", description="Total fat", unit="g")] = None
    fiber_g: Annotated[float | None, Field(db_type="DOUBLE", description="Total dietary fiber", unit="g")] = None
    sugar_g: Annotated[float | None, Field(db_type="DOUBLE", description="Total sugars", unit="g")] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        path = _find_csv(client, "daily", "nutrition")
        if not path:
            return
        for row in _read_csv(path):
            raw_date = row.pop("date", None)
            if not raw_date:
                continue
            row["date"] = str(raw_date)[:10]
            yield row


class Servings(EventTable):
    """Individual food entries from Cronometer's Servings export."""

    class _Meta:
        name = "servings"
        display_name = "Servings"
        description = "Individual food log entries from Cronometer."
        pk = ("id",)

    time_at: ClassVar[str] = "day"

    id: Annotated[str, Field(db_type="VARCHAR", description="Content-hash ID")] = ""
    day: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""
    meal: Annotated[str | None, Field(db_type="VARCHAR", description="Meal group (Breakfast, Lunch, ...)")] = None
    food_name: Annotated[str, Field(db_type="VARCHAR", description="Food item name")] = ""
    amount: Annotated[float | None, Field(db_type="DOUBLE", description="Serving amount")] = None
    energy_kcal: Annotated[float | None, Field(db_type="DOUBLE", description="Energy per serving", unit="kcal")] = None
    protein_g: Annotated[float | None, Field(db_type="DOUBLE", description="Protein per serving", unit="g")] = None
    carbs_g: Annotated[float | None, Field(db_type="DOUBLE", description="Carbs per serving", unit="g")] = None
    fat_g: Annotated[float | None, Field(db_type="DOUBLE", description="Fat per serving", unit="g")] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        path = _find_csv(client, "serving")
        if not path:
            return
        for row in _read_csv(path):
            day = str(row.pop("day", row.pop("date", "")))[:10]
            if not day:
                continue
            food = str(row.get("food_name", row.get("name", "")))
            meal = row.get("group", row.get("meal"))
            row["day"] = day
            row["food_name"] = food
            row["meal"] = str(meal) if meal else None
            raw = f"{day}:{meal}:{food}:{row.get('amount', '')}"
            row["id"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
            yield row


TABLES: tuple[type[SourceTable], ...] = (DailyNutrition, Servings)
