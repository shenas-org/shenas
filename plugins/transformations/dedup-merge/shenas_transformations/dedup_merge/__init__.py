"""Dedup/merge transformation -- unify overlapping records from multiple sources."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

import duckdb
from shenas_transformations.core import Transform

if TYPE_CHECKING:
    from shenas_transformations.core.instance import TransformInstance

log = logging.getLogger(f"shenas.{__name__}")


class DedupMergeTransform(Transform):
    """Unify records from two sources that represent the same entity.

    Matches records by overlapping time windows and configurable key
    columns. When a match is found, keeps the record from the preferred
    source and discards the duplicate. Unmatched records from both sources
    are preserved.
    """

    name = "dedup-merge"
    display_name = "Dedup/Merge Transform"
    description = "Unify overlapping records from multiple sources into a single deduplicated table."

    def execute(
        self,
        con: duckdb.DuckDBPyConnection,
        instance: TransformInstance,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        primary_source = params.get("primary_source")
        secondary_source = params.get("secondary_source")
        time_col = params.get("time_column", "start_at")
        match_window_min = params.get("match_window_minutes", 30)
        prefer = params.get("prefer", "primary")

        if not primary_source or not secondary_source:
            log.warning(
                "Dedup transform #%d missing primary_source or secondary_source",
                instance.id,
            )
            return 0

        source_name = instance.source_plugin
        target = f'"{instance.target_duckdb_schema}"."{instance.target_duckdb_table}"'

        try:
            con.execute(f"DELETE FROM {target} WHERE source IN (?, ?)", [primary_source, secondary_source])

            with contextlib.suppress(duckdb.Error):
                con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

            if prefer == "primary":
                keep_all = primary_source
                keep_unmatched = secondary_source
            else:
                keep_all = secondary_source
                keep_unmatched = primary_source

            source_schema = instance.source_duckdb_schema
            source_table = instance.source_duckdb_table

            # All records from preferred source
            con.execute(
                f"INSERT INTO {target} "
                f"SELECT *, '{device_id}' AS source_device "
                f'FROM "{source_schema}"."{source_table}" '
                f"WHERE source = ?",
                [keep_all],
            )

            # Unmatched from secondary source (no overlap within time window)
            con.execute(
                f"INSERT INTO {target} "
                f"SELECT s.*, '{device_id}' AS source_device "
                f'FROM "{source_schema}"."{source_table}" s '
                f"WHERE s.source = ? "
                f"AND NOT EXISTS ("
                f'  SELECT 1 FROM "{source_schema}"."{source_table}" p '
                f"  WHERE p.source = ? "
                f"  AND ABS(EXTRACT(EPOCH FROM (s.{time_col}::TIMESTAMP - p.{time_col}::TIMESTAMP))) "
                f"      <= ? * 60"
                f")",
                [keep_unmatched, keep_all, match_window_min],
            )

            return 1
        except Exception:
            log.exception(
                "Dedup transform #%d failed (%s -> %s)",
                instance.id,
                source_name,
                target,
            )
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "primary_source",
                "type": "text",
                "required": True,
                "description": "Primary source plugin name (e.g. garmin)",
            },
            {
                "name": "secondary_source",
                "type": "text",
                "required": True,
                "description": "Secondary source plugin name (e.g. strava)",
            },
            {
                "name": "time_column",
                "type": "text",
                "required": False,
                "description": "Timestamp column used for matching",
                "default": "start_at",
            },
            {
                "name": "match_window_minutes",
                "type": "number",
                "required": False,
                "description": "Time window in minutes for considering records as duplicates",
                "default": 30,
            },
            {
                "name": "prefer",
                "type": "select",
                "required": False,
                "description": "Which source to prefer when records overlap",
                "default": "primary",
                "options": ["primary", "secondary"],
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("primary_source"):
            msg = "primary_source is required"
            raise ValueError(msg)
        if not params.get("secondary_source"):
            msg = "secondary_source is required"
            raise ValueError(msg)


__all__ = ["DedupMergeTransform"]
