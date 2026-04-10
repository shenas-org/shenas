"""Tests for Cronometer source tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shenas_sources.cronometer.tables import DailyNutrition, Servings

if TYPE_CHECKING:
    from pathlib import Path


def test_daily_nutrition(tmp_path: Path) -> None:
    csv_file = tmp_path / "dailySummary.csv"
    csv_file.write_text(
        "Date,Completed,Energy (kcal),Protein (g),Carbs (g),Fat (g),Fiber (g),Sugars (g)\n"
        "2024-01-15,true,2100,120,250,80,30,45\n"
        "2024-01-16,true,1950,110,230,75,28,40\n"
    )
    rows = list(DailyNutrition.extract(str(tmp_path)))
    assert len(rows) == 2

    first = rows[0]
    assert first["date"] == "2024-01-15"
    assert first["energy_kcal"] == 2100.0
    assert first["protein_g"] == 120.0
    assert first["carbs_g"] == 250.0
    assert first["fat_g"] == 80.0
    assert first["fiber_g"] == 30.0


def test_servings(tmp_path: Path) -> None:
    csv_file = tmp_path / "servings.csv"
    csv_file.write_text(
        "Day,Group,Food Name,Amount,Energy (kcal),Protein (g),Carbs (g),Fat (g)\n"
        "2024-01-15,Breakfast,Oatmeal,1.5,158,5.4,27,3.2\n"
        "2024-01-15,Lunch,Chicken Breast,200,330,62,0,7.4\n"
    )
    rows = list(Servings.extract(str(tmp_path)))
    assert len(rows) == 2

    assert rows[0]["day"] == "2024-01-15"
    assert rows[0]["food_name"] == "Oatmeal"
    assert rows[0]["meal"] == "Breakfast"
    assert rows[0]["energy_kcal"] == 158.0
    assert rows[0]["id"]  # has content-hash ID

    assert rows[1]["food_name"] == "Chicken Breast"
    assert rows[1]["meal"] == "Lunch"


def test_no_csv_returns_empty(tmp_path: Path) -> None:
    rows = list(DailyNutrition.extract(str(tmp_path)))
    assert rows == []
