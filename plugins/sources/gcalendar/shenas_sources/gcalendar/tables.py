"""Google Calendar raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class Event:
    """Google Calendar event."""

    __table__: ClassVar[str] = "events"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

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
    event_type: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Type: default | focusTime | outOfOffice | workingLocation"),
    ] = None
    visibility: Annotated[str | None, Field(db_type="VARCHAR", description="default | public | private | confidential")] = None
    transparency: Annotated[str | None, Field(db_type="VARCHAR", description="busy | transparent (free)")] = None
    color_id: Annotated[str | None, Field(db_type="VARCHAR", description="Color ID (joins to colors table)")] = None
    is_video_call: Annotated[bool, Field(db_type="BOOLEAN", description="Has a Meet/Zoom/etc link")] = False
    conference_url: Annotated[str | None, Field(db_type="VARCHAR", description="First conference entry-point URL")] = None
    conference_type: Annotated[
        str | None, Field(db_type="VARCHAR", description="Conference solution name (e.g. Google Meet)")
    ] = None
    recurrence_rule: Annotated[
        str | None, Field(db_type="VARCHAR", description="RRULE string for recurring events (joined)")
    ] = None
    recurring_event_id: Annotated[str | None, Field(db_type="VARCHAR", description="Parent recurring event ID")] = None
    original_start_time: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Original start of a moved recurring instance")
    ] = None
    html_link: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Link to event in Google Calendar"),
    ] = None
    created: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None
    updated: Annotated[str | None, Field(db_type="TIMESTAMP", description="Last updated timestamp")] = None


@dataclass
class EventAttendee:
    """A single attendee on a calendar event."""

    __table__: ClassVar[str] = "event_attendees"
    __pk__: ClassVar[tuple[str, ...]] = ("event_id", "email")
    __kind__: ClassVar[TableKind] = "event"

    event_id: Annotated[str, Field(db_type="VARCHAR", description="Parent event ID")]
    email: Annotated[str, Field(db_type="VARCHAR", description="Attendee email")]
    display_name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    response_status: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="needsAction | declined | tentative | accepted"),
    ] = None
    optional: Annotated[bool, Field(db_type="BOOLEAN", description="Optional attendee")] = False
    organizer: Annotated[bool, Field(db_type="BOOLEAN", description="Organizer flag")] = False
    is_self: Annotated[bool, Field(db_type="BOOLEAN", description="The authenticated user")] = False


@dataclass
class Color:
    """Google Calendar event color palette entry."""

    __table__: ClassVar[str] = "colors"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "dimension"

    id: Annotated[str, Field(db_type="VARCHAR", description="Color ID")]
    background: Annotated[str | None, Field(db_type="VARCHAR", description="Background hex color")] = None
    foreground: Annotated[str | None, Field(db_type="VARCHAR", description="Foreground hex color")] = None


@dataclass
class Calendar:
    """Google Calendar entry."""

    __table__: ClassVar[str] = "calendars"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "dimension"

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
