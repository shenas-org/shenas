from __future__ import annotations

from unittest.mock import MagicMock

from shenas_pipes.duolingo.source import courses, daily_xp, user_profile


class TestDailyXp:
    def test_yields_summaries(self) -> None:
        client = MagicMock()
        client.get_xp_summaries.return_value = [
            {"date": "2026-03-28", "gainedXp": 150, "numSessions": 3, "totalSessionTime": 900},
            {"date": "2026-03-29", "gainedXp": 80, "numSessions": 2, "totalSessionTime": 600},
        ]

        results = list(daily_xp(client, "2026-03-28"))
        assert len(results) == 2
        assert results[0]["xp_gained"] == 150
        assert results[1]["num_sessions"] == 2

    def test_skips_entries_without_date(self) -> None:
        client = MagicMock()
        client.get_xp_summaries.return_value = [
            {"gainedXp": 50},
            {"date": "2026-03-29", "gainedXp": 80},
        ]

        results = list(daily_xp(client, "2026-03-28"))
        assert len(results) == 1


class TestCourses:
    def test_yields_courses(self) -> None:
        client = MagicMock()
        client.get_courses.return_value = [
            {"language": "German", "language_code": "de", "from_language": "en", "xp": 5000, "crowns": 50, "level": 12},
        ]

        results = list(courses(client))
        assert len(results) == 1
        assert results[0]["language"] == "German"


class TestUserProfile:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        client.get_user.return_value = {
            "id": 12345,
            "username": "testuser",
            "name": "Test",
            "streak_extended_today": 42,
            "longest_streak": 100,
            "totalXp": 50000,
            "creationDate": 1600000000,
            "learningLanguage": "de",
            "fromLanguage": "en",
        }

        results = list(user_profile(client))
        assert len(results) == 1
        assert results[0]["username"] == "testuser"
        assert results[0]["streak"] == 42
        assert results[0]["total_xp"] == 50000
