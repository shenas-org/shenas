"""Canonical location metrics -- geofence-categorized location visits."""

from __future__ import annotations

from typing import Annotated

from app.table import Field
from shenas_datasets.core import EventMetricTable

Source = Annotated[str, Field(db_type="VARCHAR", description="Source plugin (e.g. gtakeout)", display_name="Source")]


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
        time_at = "arrived_at"

    source: Source
    source_id: Annotated[
        str, Field(db_type="VARCHAR", description="Unique visit identifier within the source", display_name="Source ID")
    ]
    arrived_at: Annotated[str, Field(db_type="TIMESTAMP", description="Arrival timestamp", display_name="Arrived At")]
    left_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Departure timestamp", display_name="Left At")] = (
        None
    )
    duration_min: Annotated[
        float | None, Field(db_type="DOUBLE", description="Time spent at location", display_name="Duration", unit="min")
    ] = None
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Visit latitude", display_name="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Visit longitude", display_name="Longitude")] = None
    geofence: Annotated[
        str | None, Field(db_type="VARCHAR", description="Matched geofence name (e.g. Home, Work)", display_name="Geofence")
    ] = None
    geofence_category: Annotated[
        str | None, Field(db_type="VARCHAR", description="Matched geofence category", display_name="Geofence Category")
    ] = None
    place_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Original place name from the source", display_name="Place Name")
    ] = None
    confidence: Annotated[
        str | None, Field(db_type="VARCHAR", description="Location confidence level", display_name="Confidence")
    ] = None


ALL_TABLES = [LocationVisit]
