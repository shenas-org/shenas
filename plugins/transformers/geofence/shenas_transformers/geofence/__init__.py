"""Geofence transformer plugin -- categorize locations using DuckDB spatial."""

from __future__ import annotations

import json
import logging
from typing import Any

import duckdb
from shenas_transformers.core import Transformer
from shenas_transformers.core.transform import Transform

log = logging.getLogger(f"shenas.{__name__}")


class GeofenceTransformer(Transformer):
    """Categorize location data by matching coordinates against user-defined geofences."""

    name = "geofence"
    display_name = "Geofence Transformer"
    description = "Categorize location data by matching coordinates against user-defined geofences."

    def execute(
        self,
        instance: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        import contextlib

        params = instance.get_params()
        lat_col = params.get("latitude_column", "latitude")
        lon_col = params.get("longitude_column", "longitude")
        time_col = params.get("time_column", "start_timestamp")
        end_time_col = params.get("end_time_column", "end_timestamp")
        place_col = params.get("place_name_column", "place_name")
        id_expr = params.get("id_expression", f"{time_col} || '_' || REPLACE({place_col}, ' ', '_')")
        filter_where = params.get("filter_where", "")
        confidence_col = params.get("confidence_column", "confidence")
        source_name = instance.source_plugin

        target = f'"{instance.target_ref.schema}"."{instance.target_ref.table}"'
        source = f'"{instance.source_ref.schema}"."{instance.source_ref.table}"'

        try:
            from app.database import cursor

            with cursor() as cur:
                cur.execute("INSTALL spatial; LOAD spatial;")
                cur.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

                sql = f"""
                    SELECT
                        '{source_name}' AS source,
                        ({id_expr}) AS source_id,
                        v.{time_col}::TIMESTAMP AS arrived_at,
                        v.{end_time_col}::TIMESTAMP AS left_at,
                        CASE
                            WHEN v.{time_col} IS NOT NULL AND v.{end_time_col} IS NOT NULL
                            THEN EXTRACT(EPOCH FROM (
                                v.{end_time_col}::TIMESTAMP - v.{time_col}::TIMESTAMP
                            )) / 60.0
                            ELSE NULL
                        END AS duration_min,
                        v.{lat_col} AS latitude,
                        v.{lon_col} AS longitude,
                        g.name AS geofence,
                        g.category AS geofence_category,
                        v.{place_col} AS place_name,
                        v.{confidence_col} AS confidence,
                        '{device_id}' AS source_device
                    FROM {source} v
                    LEFT JOIN shenas_system.geofences g
                        ON ST_DWithin(
                            ST_Point(v.{lon_col}, v.{lat_col}),
                            ST_Point(g.longitude, g.latitude),
                            g.radius_m
                        )
                        AND v.{lat_col} != 0 AND v.{lon_col} != 0
                    WHERE v.{time_col} IS NOT NULL
                """

                if filter_where:
                    sql += f" AND {filter_where}"

                with contextlib.suppress(duckdb.Error):
                    cur.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                cur.execute(f"INSERT INTO {target} {sql}")
            return 1
        except Exception:
            log.exception("Geofence transform #%d failed (%s -> %s)", instance.id, source_name, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "latitude_column",
                "label": "Latitude column",
                "type": "text",
                "required": False,
                "description": "Latitude column name",
                "default": "latitude",
            },
            {
                "name": "longitude_column",
                "label": "Longitude column",
                "type": "text",
                "required": False,
                "description": "Longitude column name",
                "default": "longitude",
            },
            {
                "name": "time_column",
                "label": "Arrival time column",
                "type": "text",
                "required": False,
                "description": "Arrival time column",
                "default": "start_timestamp",
            },
            {
                "name": "end_time_column",
                "label": "Departure time column",
                "type": "text",
                "required": False,
                "description": "Departure time column",
                "default": "end_timestamp",
            },
            {
                "name": "place_name_column",
                "label": "Place name column",
                "type": "text",
                "required": False,
                "description": "Place name column",
                "default": "place_name",
            },
            {
                "name": "confidence_column",
                "label": "Confidence column",
                "type": "text",
                "required": False,
                "description": "Confidence column",
                "default": "confidence",
            },
            {
                "name": "id_expression",
                "label": "ID expression",
                "type": "text",
                "required": False,
                "description": "SQL expression for source_id",
            },
            {
                "name": "filter_where",
                "label": "Filter (WHERE clause)",
                "type": "text",
                "required": False,
                "description": "Additional WHERE clause filter",
            },
        ]

    def seed_defaults_for_source(self, source_name: str) -> None:
        if source_name != "gtakeout":
            return

        defaults = [
            {
                "source_duckdb_schema": "gtakeout",
                "source_duckdb_table": "location_visits",
                "target_duckdb_schema": "metrics",
                "target_duckdb_table": "location_visits",
                "description": "Categorize Google Takeout location visits using geofences",
                "params": json.dumps(
                    {
                        "latitude_column": "latitude",
                        "longitude_column": "longitude",
                        "time_column": "start_timestamp",
                        "end_time_column": "end_timestamp",
                        "place_name_column": "place_name",
                        "confidence_column": "confidence",
                        "filter_where": "v.type = 'visit'",
                    }
                ),
            }
        ]
        Transform.seed_defaults(source_name, "geofence", defaults)


__all__ = ["GeofenceTransform"]
