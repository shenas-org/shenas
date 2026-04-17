"""Reverse geocode cache table -- stores coordinate-to-place lookups."""

from __future__ import annotations

from typing import Annotated

from app.schema import CACHE
from app.table import Field, Table


class ReverseGeocodeCacheEntry(Table):
    """Cached reverse geocode result keyed on coordinate hash."""

    class _Meta:
        name = "reverse_geocode_cache"
        display_name = "Reverse Geocode Cache"
        description = "Cached coordinate-to-place lookups."
        schema = CACHE
        pk = ("coord_hash",)

    coord_hash: Annotated[str, Field(db_type="VARCHAR", description="SHA-256 prefix of lat,lon")] = ""
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Longitude")] = None
    place_name: Annotated[str | None, Field(db_type="VARCHAR", description="Resolved place name")] = None
    address: Annotated[str | None, Field(db_type="VARCHAR", description="Full address")] = None
    provider: Annotated[str | None, Field(db_type="VARCHAR", description="Geocoding provider")] = None
    fetched_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When fetched", db_default="current_timestamp")
    ] = None
