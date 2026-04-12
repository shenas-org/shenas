"""Reverse geocode transformation -- lat/lng to place name via geopy."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

import duckdb
from shenas_transformations.core import Transform, TransformConfig

if TYPE_CHECKING:
    from shenas_transformations.core.instance import TransformInstance

from dataclasses import dataclass
from typing import Annotated

from shenas_plugins.core.table import Field

log = logging.getLogger(f"shenas.{__name__}")


@dataclass
class _ReverseGeocodeConfig(TransformConfig):
    provider: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Geocoding provider: nominatim, google, or mapbox",
            db_default="'nominatim'",
            ui_widget="select",
            options=("nominatim", "google", "mapbox"),
        ),
    ] = "nominatim"
    api_key: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="API key (required for google/mapbox, not for nominatim)",
            category="secret",
            ui_widget="password",
        ),
    ] = None


class ReverseGeocodeTransform(Transform):
    """Convert latitude/longitude to place names using a reverse geocoding API."""

    name = "reverse-geocode"
    display_name = "Reverse Geocode Transform"
    description = "Convert latitude/longitude to place names using a reverse geocoding API."

    Config = _ReverseGeocodeConfig

    def execute(
        self,
        con: duckdb.DuckDBPyConnection,
        instance: TransformInstance,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        lat_col = params.get("latitude_column", "latitude")
        lon_col = params.get("longitude_column", "longitude")
        output_col = params.get("output_column", "place_name")
        source_name = instance.source_plugin
        source = f'"{instance.source_duckdb_schema}"."{instance.source_duckdb_table}"'
        target = f'"{instance.target_duckdb_schema}"."{instance.target_duckdb_table}"'

        try:
            con.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

            # Ensure reverse geocode cache
            con.execute("""
                CREATE TABLE IF NOT EXISTS shenas_system.reverse_geocode_cache (
                    coord_hash VARCHAR PRIMARY KEY,
                    latitude DOUBLE,
                    longitude DOUBLE,
                    place_name VARCHAR,
                    address VARCHAR,
                    provider VARCHAR,
                    fetched_at TIMESTAMP DEFAULT current_timestamp
                )
            """)

            # Read distinct coordinate pairs (rounded to ~11m precision)
            rows = con.execute(
                f"SELECT DISTINCT ROUND({lat_col}, 4) AS lat, ROUND({lon_col}, 4) AS lon "
                f"FROM {source} "
                f"WHERE {lat_col} IS NOT NULL AND {lon_col} IS NOT NULL "
                f"AND {lat_col} != 0 AND {lon_col} != 0"
            ).fetchall()

            coords = [(r[0], r[1]) for r in rows]

            # Check cache
            cached: dict[tuple[float, float], str] = {}
            for lat, lon in coords:
                coord_hash = hashlib.sha256(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:16]
                result = con.execute(
                    "SELECT place_name FROM shenas_system.reverse_geocode_cache WHERE coord_hash = ?",
                    [coord_hash],
                ).fetchone()
                if result:
                    cached[(lat, lon)] = result[0]

            # Reverse geocode uncached
            uncached = [c for c in coords if c not in cached]
            if uncached:
                config = self.Config.read_row() or {}
                provider = config.get("provider", "nominatim")
                api_key = config.get("api_key")
                resolved = _batch_reverse_geocode(uncached, provider, api_key)

                for (lat, lon), (place, address) in resolved.items():
                    coord_hash = hashlib.sha256(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:16]
                    con.execute(
                        "INSERT OR REPLACE INTO shenas_system.reverse_geocode_cache "
                        "(coord_hash, latitude, longitude, place_name, address, provider) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        [coord_hash, lat, lon, place, address, provider],
                    )
                    cached[(lat, lon)] = place

            # Write: join source with cached results
            import contextlib

            with contextlib.suppress(duckdb.Error):
                con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

            con.execute(
                f"INSERT INTO {target} "
                f"SELECT s.*, rc.place_name AS {output_col}, '{device_id}' AS source_device "
                f"FROM {source} s "
                f"LEFT JOIN shenas_system.reverse_geocode_cache rc "
                f"ON ROUND(s.{lat_col}, 4)::VARCHAR || ',' || ROUND(s.{lon_col}, 4)::VARCHAR "
                f"= rc.latitude::VARCHAR || ',' || rc.longitude::VARCHAR"
            )
            return 1
        except Exception:
            log.exception(
                "Reverse geocode transform #%d failed (%s -> %s)",
                instance.id,
                source_name,
                target,
            )
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
                "name": "output_column",
                "label": "Output column",
                "type": "text",
                "required": False,
                "description": "Output column name for the place name",
                "default": "place_name",
            },
        ]


def _batch_reverse_geocode(
    coords: list[tuple[float, float]],
    provider: str = "nominatim",
    api_key: str | None = None,
) -> dict[tuple[float, float], tuple[str, str]]:
    """Reverse geocode coordinates. Returns {(lat, lon): (place_name, address)}."""
    from geopy.extra.rate_limiter import RateLimiter
    from geopy.geocoders import get_geocoder_for_service

    geocoder_cls = get_geocoder_for_service(provider)
    kwargs: dict[str, Any] = {}
    if provider == "nominatim":
        kwargs["user_agent"] = "shenas"
    if api_key:
        kwargs["api_key"] = api_key

    geocoder = geocoder_cls(**kwargs)
    reverse = RateLimiter(geocoder.reverse, min_delay_seconds=1)

    results: dict[tuple[float, float], tuple[str, str]] = {}
    for lat, lon in coords:
        try:
            location = reverse(f"{lat}, {lon}")
            if location:
                raw = location.raw or {}
                place = raw.get("name", "") or raw.get("display_name", location.address or "")
                results[(lat, lon)] = (place, location.address or "")
        except Exception:
            log.warning("Reverse geocode failed for (%s, %s)", lat, lon)
    return results


__all__ = ["ReverseGeocodeTransform"]
