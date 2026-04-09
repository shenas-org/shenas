"""Geofence: named circular regions for categorizing location data.

A geofence defines a center (latitude, longitude) and a radius in meters.
Location records and visits that fall within the circle are tagged with
the geofence's ``name`` by the gtakeout -> metrics.location_visits
transform. Users manage geofences via the CLI or GraphQL.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table

log = logging.getLogger(f"shenas.{__name__}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Geofence(Table):
    """A named circular geofence stored in ``shenas_system.geofences``.

    Each row defines a center point and radius. SQL transforms use
    :func:`ensure_haversine_macro` to compute distances and match
    location records against geofences.
    """

    class _Meta:
        name = "geofences"
        display_name = "Geofences"
        description = "User-defined circular geofences for categorizing location data."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Geofence ID", db_default="nextval('shenas_system.geofence_seq')"),
    ] = 0
    name: Annotated[str, Field(db_type="VARCHAR", description="Geofence label (e.g. Home, Work, Library)")] = ""
    latitude: Annotated[
        float,
        Field(db_type="DOUBLE", description="Center latitude in decimal degrees", value_range=(-90, 90)),
    ] = 0.0
    longitude: Annotated[
        float,
        Field(db_type="DOUBLE", description="Center longitude in decimal degrees", value_range=(-180, 180)),
    ] = 0.0
    radius_m: Annotated[
        float,
        Field(db_type="DOUBLE", description="Radius in meters", unit="m", value_range=(1, 100_000)),
    ] = 200.0
    category: Annotated[
        str,
        Field(db_type="VARCHAR", description="Optional grouping category (e.g. personal, work)", db_default="''"),
    ] = ""
    added_at: Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None = (
        None
    )
    updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        latitude: float,
        longitude: float,
        radius_m: float = 200.0,
        category: str = "",
    ) -> Geofence:
        g = cls(
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            category=category,
        )
        return g.insert()

    def update(
        self,
        *,
        name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_m: float | None = None,
        category: str | None = None,
    ) -> Geofence:
        if name is not None:
            self.name = name
        if latitude is not None:
            self.latitude = latitude
        if longitude is not None:
            self.longitude = longitude
        if radius_m is not None:
            self.radius_m = radius_m
        if category is not None:
            self.category = category
        self.updated_at = _now_iso()
        return self.save()


def ensure_haversine_macro(con: Any) -> None:
    """Create a DuckDB macro that computes haversine distance in meters.

    ``shenas_system.haversine_m(lat1, lon1, lat2, lon2)`` returns the
    great-circle distance between two points in **meters**.
    """
    con.execute("""
        CREATE OR REPLACE MACRO shenas_system.haversine_m(lat1, lon1, lat2, lon2) AS
            6371000.0 * 2 * ASIN(
                SQRT(
                    POW(SIN(RADIANS(lat2 - lat1) / 2), 2)
                    + COS(RADIANS(lat1)) * COS(RADIANS(lat2))
                      * POW(SIN(RADIANS(lon2 - lon1) / 2), 2)
                )
            )
    """)
