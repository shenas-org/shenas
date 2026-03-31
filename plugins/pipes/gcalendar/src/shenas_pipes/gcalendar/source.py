"""Google Calendar dlt resources -- events, calendars."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt

from shenas_pipes.core.utils import resolve_start_date


@dlt.resource(write_disposition="merge", primary_key="id")
def events(
    service: Any,
    start_date: str = "30 days ago",
    calendar_id: str = "primary",
) -> Iterator[dict[str, Any]]:
    """Yield calendar events from the given date onwards."""
    import pendulum

    resolved = resolve_start_date(start_date)
    time_min = pendulum.parse(resolved).start_of("day").isoformat()

    page_token: str | None = None
    while True:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
                pageToken=page_token,
            )
            .execute()
        )

        for event in result.get("items", []):
            start = event.get("start", {})
            end = event.get("end", {})

            yield {
                "id": event["id"],
                "calendar_id": calendar_id,
                "summary": event.get("summary", ""),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start_date": start.get("date") or start.get("dateTime", ""),
                "end_date": end.get("date") or end.get("dateTime", ""),
                "all_day": "date" in start,
                "status": event.get("status", ""),
                "creator_email": event.get("creator", {}).get("email", ""),
                "organizer_email": event.get("organizer", {}).get("email", ""),
                "attendees_count": len(event.get("attendees", [])),
                "recurring_event_id": event.get("recurringEventId"),
                "html_link": event.get("htmlLink", ""),
                "created": event.get("created", ""),
                "updated": event.get("updated", ""),
            }

        page_token = result.get("nextPageToken")
        if not page_token:
            break


@dlt.resource(write_disposition="replace")
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
