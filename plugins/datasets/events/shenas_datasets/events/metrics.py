"""Canonical event metrics -- a unified timeline of events from all sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field

# Shared type aliases
Timestamp = Annotated[str, Field(db_type="TIMESTAMP", description="Event start time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Source plugin (e.g. gcalendar, spotify, garmin)")]


@dataclass
class Event:
    """A single event in the unified timeline.

    Events come from different sources: calendar appointments, music plays,
    workouts, meals, etc. All share a start time, source, and title. Optional
    fields capture duration, location, category, and source-specific metadata.
    """

    __table__: ClassVar[str] = "events"
    __pk__: ClassVar[tuple[str, ...]] = ("source", "source_id")

    source: Source
    source_id: Annotated[
        str, Field(db_type="VARCHAR", description="Unique ID within the source (e.g. calendar event ID, track URI)")
    ]
    start_at: Timestamp
    end_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Event end time (null for instantaneous events)")] = (
        None
    )
    duration_min: Annotated[float | None, Field(db_type="DOUBLE", description="Duration in minutes", unit="min")] = None
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Event title or name")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Event description or details")] = None
    location: Annotated[str | None, Field(db_type="VARCHAR", description="Location name or address")] = None
    category: Annotated[
        str | None, Field(db_type="VARCHAR", description="Event category (e.g. meeting, workout, music, meal)")
    ] = None
    all_day: Annotated[bool, Field(db_type="BOOLEAN", description="Whether this is an all-day event")] = False
    metadata: Annotated[str | None, Field(db_type="JSON", description="Source-specific metadata as JSON")] = None


ALL_TABLES = [Event]
