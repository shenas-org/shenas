"""Geocode transformer plugin -- address string to lat/lng via geopy."""

from __future__ import annotations

import contextlib
import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import duckdb
from shenas_transformers.core import Transformer, TransformerConfig

from app.table import Field

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform

log = logging.getLogger(f"shenas.{__name__}")


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


class GeocodeTransformer(Transformer):
    """Convert address strings to latitude/longitude using a geocoding API."""

    name = "geocode"
    display_name = "Geocode Transformer"
    description = "Convert address strings to latitude/longitude using a geocoding API."

    Config = _GeocodeConfig

    def execute(
        self,
        instance: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        address_col = params.get("address_column")
        if not address_col:
            log.warning("Geocode transform #%d missing address_column param", instance.id)
            return 0

        lat_out = params.get("latitude_output", "latitude")
        lon_out = params.get("longitude_output", "longitude")
        source_name = instance.source_plugin
        source = f'"{instance.source_ref.schema}"."{instance.source_ref.table}"'
        target = f'"{instance.target_ref.schema}"."{instance.target_ref.table}"'

        try:
            from app.database import cursor

            with cursor() as cur:
                cur.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shenas_system.geocode_cache (
                        address_hash VARCHAR PRIMARY KEY,
                        address VARCHAR,
                        latitude DOUBLE,
                        longitude DOUBLE,
                        provider VARCHAR,
                        fetched_at TIMESTAMP DEFAULT current_timestamp
                    )
                """)

                rows = cur.execute(
                    f"SELECT DISTINCT {address_col} AS addr FROM {source} "
                    f"WHERE {address_col} IS NOT NULL AND TRIM({address_col}) != ''"
                ).fetchall()

                addresses = [r[0] for r in rows]

                cached: dict[str, tuple[float, float]] = {}
                for addr in addresses:
                    addr_hash = hashlib.sha256(addr.encode()).hexdigest()[:16]
                    result = cur.execute(
                        "SELECT latitude, longitude FROM shenas_system.geocode_cache WHERE address_hash = ?",
                        [addr_hash],
                    ).fetchone()
                    if result:
                        cached[addr] = (result[0], result[1])

            uncached = [a for a in addresses if a not in cached]
            if uncached:
                config = self.Config.read_row() or {}
                provider = config.get("provider", "nominatim")
                api_key = config.get("api_key")
                geocoded = _batch_geocode(uncached, provider, api_key)

                with cursor() as cur:
                    for addr, (lat, lng) in geocoded.items():
                        addr_hash = hashlib.sha256(addr.encode()).hexdigest()[:16]
                        cur.execute(
                            "INSERT OR REPLACE INTO shenas_system.geocode_cache "
                            "(address_hash, address, latitude, longitude, provider) "
                            "VALUES (?, ?, ?, ?, ?)",
                            [addr_hash, addr, lat, lng, provider],
                        )
                        cached[addr] = (lat, lng)

            with cursor() as cur:
                with contextlib.suppress(duckdb.Error):
                    cur.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                cur.execute(
                    f"INSERT INTO {target} "
                    f"SELECT s.*, c.latitude AS {lat_out}, c.longitude AS {lon_out}, "
                    f"'{device_id}' AS source_device "
                    f"FROM {source} s "
                    f"LEFT JOIN shenas_system.geocode_cache c "
                    f"ON SHA256(s.{address_col})[:16] = c.address_hash"
                )
            return 1
        except Exception:
            log.exception("Geocode transform #%d failed (%s -> %s)", instance.id, source_name, target)
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
            log.warning("Geocode failed for '%s'", addr)
    return results


__all__ = ["GeocodeTransform"]
