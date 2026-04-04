"""Google Calendar raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class Event:
    """Google Calendar event."""

    __table__: ClassVar[str] = "events"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Event ID")]
    calendar_id: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar ID")] = None
    summary: Annotated[str | None, Field(db_type="VARCHAR", description="Event title")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Event description")] = None
    location: Annotated[str | None, Field(db_type="VARCHAR", description="Event location")] = None
    start_date: Annotated[str | None, Field(db_type="TIMESTAMP", description="Start datetime")] = None
    end_date: Annotated[str | None, Field(db_type="TIMESTAMP", description="End datetime")] = None
    all_day: Annotated[bool, Field(db_type="BOOLEAN", description="Whether this is an all-day event")] = False
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Event status")] = None
    creator_email: Annotated[str | None, Field(db_type="VARCHAR", description="Creator email")] = None
    organizer_email: Annotated[str | None, Field(db_type="VARCHAR", description="Organizer email")] = None
    attendees_count: Annotated[int, Field(db_type="INTEGER", description="Number of attendees")] = 0
    recurring_event_id: Annotated[str | None, Field(db_type="VARCHAR", description="Parent recurring event ID")] = None
    html_link: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Link to event in Google Calendar"),
    ] = None
    created: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None
    updated: Annotated[str | None, Field(db_type="TIMESTAMP", description="Last updated timestamp")] = None


@dataclass
class Calendar:
    """Google Calendar entry."""

    __table__: ClassVar[str] = "calendars"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Calendar ID")]
    summary: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar name")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Calendar description")] = None
    primary: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Whether this is the primary calendar"),
    ] = False
    access_role: Annotated[str | None, Field(db_type="VARCHAR", description="Access role")] = None
    time_zone: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar time zone")] = None
    background_color: Annotated[str | None, Field(db_type="VARCHAR", description="Background color")] = None
    foreground_color: Annotated[str | None, Field(db_type="VARCHAR", description="Foreground color")] = None
