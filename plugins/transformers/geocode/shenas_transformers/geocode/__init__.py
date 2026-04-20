"""Geocode transformer plugin -- address string to lat/lng via geopy."""

from __future__ import annotations

import contextlib
import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import duckdb
from shenas_transformers.core import ColumnTransformer, TransformerConfig

from app.plugin import Plugin
from app.table import Field

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform


@dataclass
class _GeocodeConfig(TransformerConfig):
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


class GeocodeTransformer(ColumnTransformer):
    """Convert address strings to latitude/longitude using a geocoding API."""

    name = "geocode"
    display_name = "Geocode Transformer"
    description = "Convert address strings to latitude/longitude using a geocoding API."

    Config = _GeocodeConfig

    def execute(
        self,
        transform: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        from app.database import cursor

        params = transform.get_params()
        address_col = params.get("address_column")
        if not address_col:
            self.log.warning("Geocode transform #%d missing address_column param", transform.id)
            return 0

        lat_out = params.get("latitude_output", "latitude")
        lon_out = params.get("longitude_output", "longitude")
        source_name = transform.source_plugin
        source = f'"{transform.source_ref.schema}"."{transform.source_ref.table}"'
        target = f'"{transform.target_ref.schema}"."{transform.target_ref.table}"'

        try:
            with cursor() as con:
                con.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

                # Ensure geocode cache table exists
                from shenas_transformers.geocode.cache import GeocodeCacheEntry

                GeocodeCacheEntry.ensure()

                # Read distinct addresses that need geocoding
                rows = con.execute(
                    f"SELECT DISTINCT {address_col} AS addr FROM {source} "
                    f"WHERE {address_col} IS NOT NULL AND TRIM({address_col}) != ''"
                ).fetchall()

                addresses = [r[0] for r in rows]

                # Check cache for existing results
                cached: dict[str, tuple[float, float]] = {}
                for addr in addresses:
                    addr_hash = hashlib.sha256(addr.encode()).hexdigest()[:16]
                    entry = GeocodeCacheEntry.find(addr_hash)
                    if entry and entry.latitude is not None and entry.longitude is not None:
                        cached[addr] = (entry.latitude, entry.longitude)

                # Geocode uncached addresses
                uncached = [a for a in addresses if a not in cached]
                if uncached:
                    config = self.Config.read_row() or {}
                    provider = config.get("provider", "nominatim")
                    api_key = config.get("api_key")
                    geocoded = _batch_geocode(uncached, provider, api_key)

                    for addr, (lat, lng) in geocoded.items():
                        addr_hash = hashlib.sha256(addr.encode()).hexdigest()[:16]
                        GeocodeCacheEntry.from_row((addr_hash, addr, lat, lng, provider, None)).upsert()
                        cached[addr] = (lat, lng)

                # Write results: join source with cached geocode results
                # Register the cache as a temp view for the JOIN
                with contextlib.suppress(duckdb.Error):
                    con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                con.execute(
                    f"INSERT INTO {target} "
                    f"SELECT s.*, c.latitude AS {lat_out}, c.longitude AS {lon_out}, "
                    f"'{device_id}' AS source_device "
                    f"FROM {source} s "
                    f"LEFT JOIN cache.geocode_cache c "
                    f"ON SHA256(s.{address_col})[:16] = c.address_hash"
                )
                return 1
        except Exception:
            self.log.exception("Geocode transform #%d failed (%s -> %s)", transform.id, source_name, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "address_column",
                "label": "Address column",
                "type": "source_column",
                "required": True,
                "description": "Column containing address strings",
            },
            {
                "name": "latitude_output",
                "label": "Latitude output column",
                "type": "text",
                "required": False,
                "description": "Output latitude column name",
                "default": "latitude",
            },
            {
                "name": "longitude_output",
                "label": "Longitude output column",
                "type": "text",
                "required": False,
                "description": "Output longitude column name",
                "default": "longitude",
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("address_column"):
            msg = "address_column is required"
            raise ValueError(msg)


def _batch_geocode(
    addresses: list[str],
    provider: str = "nominatim",
    api_key: str | None = None,
) -> dict[str, tuple[float, float]]:
    """Geocode a list of addresses. Returns {address: (lat, lng)}."""
    from geopy.extra.rate_limiter import RateLimiter
    from geopy.geocoders import get_geocoder_for_service

    geocoder_cls = get_geocoder_for_service(provider)
    kwargs: dict[str, Any] = {}
    if provider == "nominatim":
        kwargs["user_agent"] = "shenas"
    if api_key:
        kwargs["api_key"] = api_key

    geocoder = geocoder_cls(**kwargs)
    geocode = RateLimiter(geocoder.geocode, min_delay_seconds=1)

    results: dict[str, tuple[float, float]] = {}
    for addr in addresses:
        try:
            location = geocode(addr)
            if location:
                results[addr] = (location.latitude, location.longitude)
        except Exception:
            Plugin.get_logger(__name__).warning("Geocode failed for '%s'", addr)
    return results


__all__ = ["GeocodeTransform"]
