"""Reverse geocode transformation -- lat/lng to place name via geopy."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import duckdb
from shenas_transformers.core import ColumnTransformer, TransformerConfig

from app.plugin import Plugin

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform

from dataclasses import dataclass
from typing import Annotated

from app.table import Field


@dataclass
class _ReverseGeocodeConfig(TransformerConfig):
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


class ReverseGeocodeTransformer(ColumnTransformer):
    """Convert latitude/longitude to place names using a reverse geocoding API."""

    name = "reverse-geocode"
    display_name = "Reverse Geocode Transformer"
    description = "Convert latitude/longitude to place names using a reverse geocoding API."

    Config = _ReverseGeocodeConfig

    def execute(
        self,
        transform: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        from app.database import cursor

        params = transform.get_params()
        lat_col = params.get("latitude_column", "latitude")
        lon_col = params.get("longitude_column", "longitude")
        output_col = params.get("output_column", "place_name")
        source_name = transform.source_plugin
        source = f'"{transform.source_ref.schema}"."{transform.source_ref.table}"'
        target = f'"{transform.target_ref.schema}"."{transform.target_ref.table}"'

        try:
            with cursor() as con:
                con.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

                # Ensure reverse geocode cache table exists
                from shenas_transformers.reverse_geocode.cache import ReverseGeocodeCacheEntry

                ReverseGeocodeCacheEntry.ensure()

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
                    entry = ReverseGeocodeCacheEntry.find(coord_hash)
                    if entry and entry.place_name:
                        cached[(lat, lon)] = entry.place_name

                # Reverse geocode uncached
                uncached = [c for c in coords if c not in cached]
                if uncached:
                    config = self.Config.read_row() or {}
                    provider = config.get("provider", "nominatim")
                    api_key = config.get("api_key")
                    resolved = _batch_reverse_geocode(uncached, provider, api_key)

                    for (lat, lon), (place, address) in resolved.items():
                        coord_hash = hashlib.sha256(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:16]
                        ReverseGeocodeCacheEntry.from_row((coord_hash, lat, lon, place, address, provider, None)).upsert()
                        cached[(lat, lon)] = place

                # Write: join source with cached results
                import contextlib

                with contextlib.suppress(duckdb.Error):
                    con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                con.execute(
                    f"INSERT INTO {target} "
                    f"SELECT s.*, rc.place_name AS {output_col}, '{device_id}' AS source_device "
                    f"FROM {source} s "
                    f"LEFT JOIN cache.reverse_geocode_cache rc "
                    f"ON ROUND(s.{lat_col}, 4)::VARCHAR || ',' || ROUND(s.{lon_col}, 4)::VARCHAR "
                    f"= rc.latitude::VARCHAR || ',' || rc.longitude::VARCHAR"
                )
                return 1
        except Exception:
            self.log.exception(
                "Reverse geocode transform #%d failed (%s -> %s)",
                transform.id,
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
            Plugin.get_logger(__name__).warning("Reverse geocode failed for (%s, %s)", lat, lon)
    return results


__all__ = ["ReverseGeocodeTransform"]
