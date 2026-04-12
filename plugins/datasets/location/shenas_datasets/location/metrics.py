"""Canonical location metrics -- geofence-categorized location visits."""

from __future__ import annotations

from typing import Annotated, ClassVar

from app.table import Field
from shenas_datasets.core import EventMetricTable

Source = Annotated[str, Field(db_type="VARCHAR", description="Source plugin (e.g. gtakeout)")]


class LocationVisit(EventMetricTable):
    """A location visit matched against a user-defined geofence.

    Each row represents a period of time spent at a recognized place.
    The ``geofence`` column is the geofence name (Home, Work, Library, ...)
    that the visit's coordinates fell within. Visits that don't match any
    geofence are labelled with the original place name or 'unknown'.
    """

    class _Meta:
        name = "location_visits"
        display_name = "Location Visits"
        description = "Geofence-categorized location visits from all sources."
        pk = ("source", "source_id")

    time_at: ClassVar[str] = "arrived_at"

    source: Source
    source_id: Annotated[str, Field(db_type="VARCHAR", description="Unique visit identifier within the source")]
    arrived_at: Annotated[str, Field(db_type="TIMESTAMP", description="Arrival timestamp")]
    left_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Departure timestamp")] = None
    duration_min: Annotated[float | None, Field(db_type="DOUBLE", description="Time spent at location", unit="min")] = None
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Visit latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Visit longitude")] = None
    geofence: Annotated[str | None, Field(db_type="VARCHAR", description="Matched geofence name (e.g. Home, Work)")] = None
    geofence_category: Annotated[str | None, Field(db_type="VARCHAR", description="Matched geofence category")] = None
    place_name: Annotated[str | None, Field(db_type="VARCHAR", description="Original place name from the source")] = None
    confidence: Annotated[str | None, Field(db_type="VARCHAR", description="Location confidence level")] = None


ALL_TABLES = [LocationVisit]
