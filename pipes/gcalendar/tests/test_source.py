"""Tests for Google Calendar source resources."""

from unittest.mock import MagicMock

from shenas_pipes.gcalendar.source import calendars, events


class TestEvents:
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

        result = list(events(service, start_date="2026-03-01"))
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

        result = list(events(service, start_date="2026-03-01"))
        assert result[0]["all_day"] is True
        assert result[0]["start_date"] == "2026-03-28"


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
