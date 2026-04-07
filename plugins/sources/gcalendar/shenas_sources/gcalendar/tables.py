"""Google Calendar source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Notable design choices:

- ``Events`` is an ``IntervalTable`` (start + end timestamps).
- ``EventAttendees`` is an ``M2MTable`` (event <-> attendee bridge): when
  someone is removed from an invite between syncs, dlt's SCD2 closes the
  row's ``_dlt_valid_to`` instead of leaving the link alive forever.
- ``Calendars`` is a ``DimensionTable`` (SCD2). When the user renames a
  calendar, historical events still join to the old name via valid_from /
  valid_to ranges -- the previous "replace" loader silently rewrote
  history on every sync.
- ``Colors`` is a ``DimensionTable`` (SCD2) for the same reason.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.field import Field
from shenas_sources.core.table import (
    DimensionTable,
    IntervalTable,
    M2MTable,
)
from shenas_sources.core.utils import resolve_start_date

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Shared fetch helper -- pre-fetches every event from every calendar so that
# Events and EventAttendees can iterate the same data without re-calling
# the API. Passed via the `raw_events` context kwarg.
# ---------------------------------------------------------------------------


def fetch_all_events(service: Any, start_date: str = "30 days ago") -> list[tuple[str, dict[str, Any]]]:
    """Fetch every event from every calendar since `start_date`.

    Returns a list of (calendar_id, raw_event) tuples.
    """
    import pendulum

    resolved = resolve_start_date(start_date)
    time_min = pendulum.parse(resolved).start_of("day").isoformat()

    out: list[tuple[str, dict[str, Any]]] = []
    cal_list = service.calendarList().list().execute().get("items", [])
    for cal in cal_list:
        cal_id = cal["id"]
        page_token: str | None = None
        while True:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=250,
                    pageToken=page_token,
                )
                .execute()
            )
            out.extend((cal_id, event) for event in result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
    return out


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Events(IntervalTable):
    """A Google Calendar event."""

    name: ClassVar[str] = "events"
    display_name: ClassVar[str] = "Calendar Events"
    description: ClassVar[str | None] = "Events across all the user's calendars."
    pk: ClassVar[tuple[str, ...]] = ("id",)
    time_start: ClassVar[str] = "start_date"
    time_end: ClassVar[str] = "end_date"

    id: Annotated[str, Field(db_type="VARCHAR", description="Event ID")]
    calendar_id: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar ID")] = None
    summary: Annotated[str | None, Field(db_type="VARCHAR", description="Event title")] = None
    event_description: Annotated[str | None, Field(db_type="TEXT", description="Event description")] = None
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

    @staticmethod
    def _event_row(event: dict[str, Any], calendar_id: str) -> dict[str, Any]:
        """Map a raw Google Calendar event to a flat row."""
        start = event.get("start", {}) or {}
        end = event.get("end", {}) or {}
        creator = event.get("creator", {}) or {}
        organizer = event.get("organizer", {}) or {}
        conference = event.get("conferenceData") or {}
        entry_points = conference.get("entryPoints") or []
        video_entry = next((ep for ep in entry_points if ep.get("entryPointType") == "video"), None)
        conference_url = (video_entry or (entry_points[0] if entry_points else {})).get("uri")
        conference_type = (conference.get("conferenceSolution") or {}).get("name")
        recurrence_list = event.get("recurrence") or []
        original_start = event.get("originalStartTime") or {}
        original_start_time = original_start.get("dateTime") or original_start.get("date")
        return {
            "id": event["id"],
            "calendar_id": calendar_id,
            "summary": event.get("summary", ""),
            "event_description": event.get("description", ""),
            "location": event.get("location", ""),
            "start_date": start.get("date") or start.get("dateTime", ""),
            "end_date": end.get("date") or end.get("dateTime", ""),
            "all_day": "date" in start,
            "status": event.get("status", ""),
            "creator_email": creator.get("email", ""),
            "organizer_email": organizer.get("email", ""),
            "attendees_count": len(event.get("attendees") or []),
            "event_type": event.get("eventType"),
            "visibility": event.get("visibility"),
            "transparency": event.get("transparency"),
            "color_id": event.get("colorId"),
            "is_video_call": bool(conference_url),
            "conference_url": conference_url,
            "conference_type": conference_type,
            "recurrence_rule": "\n".join(recurrence_list) or None,
            "recurring_event_id": event.get("recurringEventId"),
            "original_start_time": original_start_time,
            "html_link": event.get("htmlLink", ""),
            "created": event.get("created", ""),
            "updated": event.get("updated", ""),
        }

    @classmethod
    def extract(
        cls,
        client: Any,  # noqa: ARG003
        *,
        raw_events: list[tuple[str, dict[str, Any]]] | None = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        for cal_id, event in raw_events or []:
            yield cls._event_row(event, cal_id)


class EventAttendees(M2MTable):
    """Bridge table linking events to attendees. SCD2 closes a row when removed."""

    name: ClassVar[str] = "event_attendees"
    display_name: ClassVar[str] = "Event Attendees"
    description: ClassVar[str | None] = "Attendees on calendar events (m2m bridge)."
    pk: ClassVar[tuple[str, ...]] = ("event_id", "email")

    event_id: Annotated[str, Field(db_type="VARCHAR", description="Parent event ID")]
    email: Annotated[str, Field(db_type="VARCHAR", description="Attendee email")]
    attendee_name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    response_status: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="needsAction | declined | tentative | accepted"),
    ] = None
    optional: Annotated[bool, Field(db_type="BOOLEAN", description="Optional attendee")] = False
    organizer: Annotated[bool, Field(db_type="BOOLEAN", description="Organizer flag")] = False
    is_self: Annotated[bool, Field(db_type="BOOLEAN", description="The authenticated user")] = False

    @staticmethod
    def _attendee_rows(event: dict[str, Any]) -> Iterator[dict[str, Any]]:
        for a in event.get("attendees") or []:
            email = a.get("email")
            if not email:
                continue
            yield {
                "event_id": event["id"],
                "email": email,
                "attendee_name": a.get("displayName"),
                "response_status": a.get("responseStatus"),
                "optional": bool(a.get("optional", False)),
                "organizer": bool(a.get("organizer", False)),
                "is_self": bool(a.get("self", False)),
            }

    @classmethod
    def extract(
        cls,
        client: Any,  # noqa: ARG003
        *,
        raw_events: list[tuple[str, dict[str, Any]]] | None = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        for _cal_id, event in raw_events or []:
            yield from cls._attendee_rows(event)


class Calendars(DimensionTable):
    """A Google Calendar entry. SCD2 captures rename history."""

    name: ClassVar[str] = "calendars"
    display_name: ClassVar[str] = "Calendars"
    description: ClassVar[str | None] = "Calendars the user has access to."
    pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Calendar ID")]
    summary: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar name")] = None
    calendar_description: Annotated[str | None, Field(db_type="TEXT", description="Calendar description")] = None
    primary: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Whether this is the primary calendar"),
    ] = False
    access_role: Annotated[str | None, Field(db_type="VARCHAR", description="Access role")] = None
    time_zone: Annotated[str | None, Field(db_type="VARCHAR", description="Calendar time zone")] = None
    background_color: Annotated[str | None, Field(db_type="VARCHAR", description="Background color")] = None
    foreground_color: Annotated[str | None, Field(db_type="VARCHAR", description="Foreground color")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {"maxResults": 250}
            if page_token:
                params["pageToken"] = page_token

            result = client.calendarList().list(**params).execute()
            for cal in result.get("items", []):
                yield {
                    "id": cal["id"],
                    "summary": cal.get("summary", ""),
                    "calendar_description": cal.get("description", ""),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole", ""),
                    "time_zone": cal.get("timeZone", ""),
                    "background_color": cal.get("backgroundColor", ""),
                    "foreground_color": cal.get("foregroundColor", ""),
                }

            page_token = result.get("nextPageToken")
            if not page_token:
                break


class Colors(DimensionTable):
    """Google Calendar event color palette. SCD2 captures palette changes."""

    name: ClassVar[str] = "colors"
    display_name: ClassVar[str] = "Calendar Colors"
    description: ClassVar[str | None] = "Global event color palette."
    pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Color ID")]
    background: Annotated[str | None, Field(db_type="VARCHAR", description="Background hex color")] = None
    foreground: Annotated[str | None, Field(db_type="VARCHAR", description="Foreground hex color")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        try:
            result = client.colors().get().execute()
        except Exception:
            return
        for color_id, payload in (result.get("event") or {}).items():
            yield {
                "id": str(color_id),
                "background": payload.get("background"),
                "foreground": payload.get("foreground"),
            }


TABLES: tuple[type, ...] = (Events, EventAttendees, Calendars, Colors)
