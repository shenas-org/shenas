"""Google Calendar dlt resources -- events, attendees, calendars, colors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.core.utils import resolve_start_date
from shenas_sources.gcalendar.tables import Calendar, Color, Event, EventAttendee

if TYPE_CHECKING:
    from collections.abc import Iterator


def _event_row(event: dict[str, Any], calendar_id: str) -> dict[str, Any]:
    """Map a raw Google Calendar event to a flat row matching Event."""
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
        "description": event.get("description", ""),
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


def _attendee_rows(event: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield one row per attendee on an event."""
    for a in event.get("attendees") or []:
        email = a.get("email")
        if not email:
            continue
        yield {
            "event_id": event["id"],
            "email": email,
            "display_name": a.get("displayName"),
            "response_status": a.get("responseStatus"),
            "optional": bool(a.get("optional", False)),
            "organizer": bool(a.get("organizer", False)),
            "is_self": bool(a.get("self", False)),
        }


def fetch_all_events(service: Any, start_date: str = "30 days ago") -> list[tuple[str, dict[str, Any]]]:
    """Fetch every event from every calendar since `start_date`.

    Returns a list of (calendar_id, raw_event) tuples so the events resource
    and the event_attendees resource can iterate the same data without
    re-calling the API.
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


@dlt.resource(
    name="events", write_disposition="merge", primary_key=list(Event.__pk__), columns=dataclass_to_dlt_columns(Event)
)
def events(raw_events: list[tuple[str, dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    """Yield event rows from a pre-fetched list of (calendar_id, event) tuples."""
    for cal_id, event in raw_events:
        yield _event_row(event, cal_id)


@dlt.resource(
    name="event_attendees",
    write_disposition="merge",
    primary_key=list(EventAttendee.__pk__),
    columns=dataclass_to_dlt_columns(EventAttendee),
)
def event_attendees(raw_events: list[tuple[str, dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    """Yield attendee rows from the same pre-fetched events."""
    for _, event in raw_events:
        yield from _attendee_rows(event)


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Calendar))
def calendars(service: Any) -> Iterator[dict[str, Any]]:
    """Yield all calendars the user has access to."""
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"maxResults": 250}
        if page_token:
            params["pageToken"] = page_token

        result = service.calendarList().list(**params).execute()
        for cal in result.get("items", []):
            yield {
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "description": cal.get("description", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
                "time_zone": cal.get("timeZone", ""),
                "background_color": cal.get("backgroundColor", ""),
                "foreground_color": cal.get("foregroundColor", ""),
            }

        page_token = result.get("nextPageToken")
        if not page_token:
            break


@dlt.resource(name="colors", write_disposition="replace", columns=dataclass_to_dlt_columns(Color))
def colors(service: Any) -> Iterator[dict[str, Any]]:
    """Yield Google Calendar's global event color palette."""
    try:
        result = service.colors().get().execute()
    except Exception:
        return
    for color_id, payload in (result.get("event") or {}).items():
        yield {
            "id": str(color_id),
            "background": payload.get("background"),
            "foreground": payload.get("foreground"),
        }
