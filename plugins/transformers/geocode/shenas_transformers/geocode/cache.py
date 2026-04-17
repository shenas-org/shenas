"""Geocode cache table -- stores address-to-coordinate lookups."""

from __future__ import annotations

from typing import Annotated

from app.schema import CACHE
from app.table import Field, Table


class GeocodeCacheEntry(Table):
    """Cached geocode result keyed on address hash."""

    class _Meta:
        name = "geocode_cache"
        display_name = "Geocode Cache"
        description = "Cached address-to-coordinate lookups."
        schema = CACHE
        pk = ("address_hash",)

    address_hash: Annotated[str, Field(db_type="VARCHAR", description="SHA-256 prefix of address")] = ""
    address: Annotated[str | None, Field(db_type="VARCHAR", description="Original address text")] = None
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Longitude")] = None
    provider: Annotated[str | None, Field(db_type="VARCHAR", description="Geocoding provider")] = None
    fetched_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When fetched", db_default="current_timestamp")
    ] = None
