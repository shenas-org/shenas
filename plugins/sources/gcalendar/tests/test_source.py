"""Tests for Google Calendar source resources."""

from unittest.mock import MagicMock

from shenas_sources.gcalendar.resources import (
    _attendee_rows,
    _event_row,
    calendars,
    colors,
    event_attendees,
    events,
    fetch_all_events,
)


def _make_event(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "evt1",
        "summary": "Team standup",
        "start": {"dateTime": "2026-03-28T09:00:00+01:00"},
        "end": {"dateTime": "2026-03-28T09:30:00+01:00"},
        "status": "confirmed",
        "creator": {"email": "user@example.com"},
        "organizer": {"email": "user@example.com"},
    }
    base.update(overrides)
    return base


class TestEventRow:
    def test_basic_fields(self) -> None:
        row = _event_row(_make_event(), "primary")
        assert row["id"] == "evt1"
        assert row["summary"] == "Team standup"
        assert row["all_day"] is False
        assert row["calendar_id"] == "primary"

    def test_all_day(self) -> None:
        row = _event_row(
            _make_event(start={"date": "2026-03-28"}, end={"date": "2026-03-29"}),
            "primary",
        )
        assert row["all_day"] is True
        assert row["start_date"] == "2026-03-28"

    def test_event_type_visibility_transparency_color(self) -> None:
        row = _event_row(
            _make_event(eventType="focusTime", visibility="private", transparency="transparent", colorId="9"),
            "primary",
        )
        assert row["event_type"] == "focusTime"
        assert row["visibility"] == "private"
        assert row["transparency"] == "transparent"
        assert row["color_id"] == "9"

    def test_video_call_extracted_from_conference(self) -> None:
        row = _event_row(
            _make_event(
                conferenceData={
                    "conferenceSolution": {"name": "Google Meet"},
                    "entryPoints": [
                        {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
                        {"entryPointType": "phone", "uri": "tel:+1-555-0100"},
                    ],
                }
            ),
            "primary",
        )
        assert row["is_video_call"] is True
        assert row["conference_url"] == "https://meet.google.com/abc-defg-hij"
        assert row["conference_type"] == "Google Meet"

    def test_no_conference(self) -> None:
        row = _event_row(_make_event(), "primary")
        assert row["is_video_call"] is False
        assert row["conference_url"] is None

    def test_recurrence_and_original_start(self) -> None:
        row = _event_row(
            _make_event(
                recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO", "EXDATE:20260330T080000Z"],
                recurringEventId="parent-evt",
                originalStartTime={"dateTime": "2026-03-28T08:00:00Z"},
            ),
            "primary",
        )
        assert "RRULE:FREQ=WEEKLY" in row["recurrence_rule"]
        assert row["recurring_event_id"] == "parent-evt"
        assert row["original_start_time"] == "2026-03-28T08:00:00Z"


class TestAttendeeRows:
    def test_yields_one_row_per_attendee(self) -> None:
        event = _make_event(
            attendees=[
                {"email": "alice@example.com", "displayName": "Alice", "responseStatus": "accepted"},
                {"email": "bob@example.com", "responseStatus": "declined", "optional": True},
                {"email": "user@example.com", "self": True, "responseStatus": "accepted"},
            ]
        )
        rows = list(_attendee_rows(event))
        assert len(rows) == 3
        assert rows[0]["email"] == "alice@example.com"
        assert rows[0]["response_status"] == "accepted"
        assert rows[1]["optional"] is True
        assert rows[2]["is_self"] is True

    def test_skips_attendees_without_email(self) -> None:
        event = _make_event(attendees=[{"displayName": "no-email"}, {"email": "ok@example.com"}])
        rows = list(_attendee_rows(event))
        assert len(rows) == 1
        assert rows[0]["email"] == "ok@example.com"


class TestFetchAllEvents:
    def test_combines_events_from_all_calendars(self) -> None:
        service = MagicMock()
        service.calendarList().list().execute.return_value = {"items": [{"id": "cal1"}, {"id": "cal2"}]}
        service.events().list().execute.return_value = {
            "items": [_make_event(id="evt1"), _make_event(id="evt2")],
        }

        raw = fetch_all_events(service, start_date="2026-03-01")
        # 2 events per calendar x 2 calendars
        assert len(raw) == 4
        assert raw[0][0] == "cal1"
        assert raw[2][0] == "cal2"


class TestEventsAndAttendeesResources:
    def test_events_and_attendees_share_data(self) -> None:
        raw = [
            ("primary", _make_event(id="e1")),
            (
                "primary",
                _make_event(
                    id="e2",
                    attendees=[
                        {"email": "alice@example.com", "responseStatus": "accepted"},
                        {"email": "bob@example.com", "responseStatus": "declined"},
                    ],
                ),
            ),
        ]
        event_rows = list(events(raw))
        attendee_rows = list(event_attendees(raw))
        assert [r["id"] for r in event_rows] == ["e1", "e2"]
        assert len(attendee_rows) == 2
        assert {r["email"] for r in attendee_rows} == {"alice@example.com", "bob@example.com"}


class TestCalendars:
    def test_yields_calendars(self) -> None:
        service = MagicMock()
        service.calendarList().list().execute.return_value = {
            "items": [
                {
                    "id": "primary",
                    "summary": "My Calendar",
                    "primary": True,
                    "accessRole": "owner",
                    "timeZone": "Europe/Stockholm",
                }
            ]
        }

        result = list(calendars(service))
        assert len(result) == 1
        assert result[0]["id"] == "primary"
        assert result[0]["primary"] is True


class TestColors:
    def test_yields_palette(self) -> None:
        service = MagicMock()
        service.colors().get().execute.return_value = {
            "event": {
                "1": {"background": "#a4bdfc", "foreground": "#1d1d1d"},
                "9": {"background": "#5484ed", "foreground": "#1d1d1d"},
            }
        }
        rows = list(colors(service))
        assert len(rows) == 2
        ids = {r["id"] for r in rows}
        assert ids == {"1", "9"}
        one = next(r for r in rows if r["id"] == "1")
        assert one["background"] == "#a4bdfc"

    def test_handles_failure(self) -> None:
        service = MagicMock()
        service.colors().get().execute.side_effect = RuntimeError("no scope")
        assert list(colors(service)) == []
