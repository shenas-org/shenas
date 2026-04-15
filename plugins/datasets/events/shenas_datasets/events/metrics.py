"""Canonical event metrics -- a unified timeline of events from all sources."""

from __future__ import annotations

from typing import Annotated

from app.table import Field
from shenas_datasets.core import EventMetricTable

# Shared type aliases
Timestamp = Annotated[str, Field(db_type="TIMESTAMP", description="Event start time", display_name="Event Time")]
Source = Annotated[
    str, Field(db_type="VARCHAR", description="Source plugin (e.g. gcalendar, spotify, garmin)", display_name="Source")
]


class Event(EventMetricTable):
    """A single event in the unified timeline.

    Events come from different sources: calendar appointments, music plays,
    workouts, meals, etc. All share a start time, source, and title. Optional
    fields capture duration, location, category, and source-specific metadata.
    """

    class _Meta:
        name = "events"
        display_name = "Events"
        description = "Unified timeline of events from all sources."
        pk = ("source", "source_id")
        time_at = "start_at"

    source: Source
    source_id: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Unique ID within the source (e.g. calendar event ID, track URI)",
            display_name="Source ID",
        ),
    ]
    start_at: Timestamp
    end_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Event end time (null for instantaneous events)", display_name="End Time"),
    ] = None
    duration_min: Annotated[
        float | None, Field(db_type="DOUBLE", description="Duration in minutes", display_name="Duration", unit="min")
    ] = None
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Event title or name", display_name="Title")] = None
    event_description: Annotated[
        str | None, Field(db_type="TEXT", description="Event description or details", display_name="Description")
    ] = None
    location: Annotated[
        str | None, Field(db_type="VARCHAR", description="Location name or address", display_name="Location")
    ] = None
    category: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Event category (e.g. meeting, workout, music, meal)", display_name="Category"),
    ] = None
    all_day: Annotated[
        bool, Field(db_type="BOOLEAN", description="Whether this is an all-day event", display_name="All Day")
    ] = False
    metadata: Annotated[
        str | None, Field(db_type="JSON", description="Source-specific metadata as JSON", display_name="Metadata")
    ] = None


ALL_TABLES = [Event]
