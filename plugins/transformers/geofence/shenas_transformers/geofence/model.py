"""Geofence: named circular regions for categorizing location data.

A geofence defines a center (latitude, longitude) and a radius in meters.
The geofence transformer plugin matches location records against these
regions using DuckDB's spatial extension. Users manage geofences via
the CLI or GraphQL.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from app.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Geofence(Table):
    """A named circular geofence stored in ``catalog.geofences``.

    Each row defines a center point and radius. SQL transforms use
    :func:`ensure_haversine_macro` to compute distances and match
    location records against geofences.
    """

    class _Meta:
        name = "geofences"
        display_name = "Geofences"
        description = "User-defined circular geofences for categorizing location data."
        schema = "catalog"
        pk = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Geofence ID", db_default="nextval('catalog.geofence_seq')"),
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
