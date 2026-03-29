"""Obsidian default transforms -- seeded into shenas_system.transforms on first sync."""

from __future__ import annotations

TRANSFORM_DEFAULTS = [
    {
        "source_duckdb_schema": "obsidian",
        "source_duckdb_table": "daily_notes",
        "target_duckdb_schema": "metrics",
        "target_duckdb_table": "daily_outcomes",
        "description": "Map Obsidian daily note frontmatter fields to daily outcomes metrics",
        "sql": (
            "SELECT date::DATE as date, 'obsidian' as source, "
            "mood, stress, COALESCE(productivity, productive) as productivity, "
            "CASE WHEN exercise__v_bool IS NOT NULL "
            "THEN CASE WHEN exercise__v_bool THEN 1 ELSE 0 END "
            "ELSE exercise END as exercise, "
            "friends, family, partner, learning, career, rosacea, left_ankle "
            "FROM obsidian.daily_notes WHERE date IS NOT NULL"
        ),
    },
]
