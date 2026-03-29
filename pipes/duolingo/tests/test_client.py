from __future__ import annotations

from unittest.mock import MagicMock

from shenas_pipes.duolingo.client import DuolingoClient


class TestGetCourses:
    def test_extracts_course_fields(self) -> None:
        client = DuolingoClient("fake-jwt")
        client.get_user = MagicMock(
            return_value={
                "courses": [
                    {
                        "title": "German",
                        "learningLanguage": "de",
                        "fromLanguage": "en",
                        "xp": 5000,
                        "crowns": 50,
                        "level": 12,
                    },
                ],
            }
        )

        result = client.get_courses()
        assert len(result) == 1
        assert result[0]["language"] == "German"
        assert result[0]["xp"] == 5000
        client.close()
