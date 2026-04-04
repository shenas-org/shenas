"""Tests for Google Calendar source resources."""

from unittest.mock import MagicMock

from shenas_pipes.gcalendar.source import _fetch_events, all_events, calendars


class TestFetchEvents:
    def test_yields_events(self) -> None:
        service = MagicMock()
        service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "evt1",
                    "summary": "Team standup",
                    "start": {"dateTime": "2026-03-28T09:00:00+01:00"},
                    "end": {"dateTime": "2026-03-28T09:30:00+01:00"},
                    "status": "confirmed",
                    "creator": {"email": "user@example.com"},
                    "organizer": {"email": "user@example.com"},
                }
            ]
        }

        result = list(_fetch_events(service, "primary", "2026-03-01T00:00:00"))
        assert len(result) == 1
        assert result[0]["id"] == "evt1"
        assert result[0]["summary"] == "Team standup"
        assert result[0]["all_day"] is False

    def test_all_day_event(self) -> None:
        service = MagicMock()
        service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "evt2",
                    "summary": "Holiday",
                    "start": {"date": "2026-03-28"},
                    "end": {"date": "2026-03-29"},
                    "status": "confirmed",
                }
            ]
        }

        result = list(_fetch_events(service, "primary", "2026-03-01T00:00:00"))
        assert result[0]["all_day"] is True
        assert result[0]["start_date"] == "2026-03-28"


class TestAllEvents:
    def test_fetches_from_all_calendars(self) -> None:
        service = MagicMock()
        service.calendarList().list().execute.return_value = {"items": [{"id": "cal1"}, {"id": "cal2"}]}
        service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "evt1",
                    "start": {"dateTime": "2026-03-28T09:00:00"},
                    "end": {"dateTime": "2026-03-28T10:00:00"},
                }
            ]
        }

        result = list(all_events(service, start_date="2026-03-01"))
        # 1 event per calendar x 2 calendars
        assert len(result) == 2
        assert result[0]["calendar_id"] == "cal1"
        assert result[1]["calendar_id"] == "cal2"


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
