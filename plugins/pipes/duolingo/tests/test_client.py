from __future__ import annotations

from unittest.mock import MagicMock

from shenas_pipes.duolingo.client import DuolingoClient, _user_id_from_jwt

# Valid JWT with sub=198910275
TEST_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJleHAiOjYzMDcyMDAwMDAsImlhdCI6MCwic3ViIjoxOTg5MTAyNzV9"
    ".UdV0kk6TDOIfwH5yQqrASZrQ4R8kF7aiXyRKIp4sN3U"
)


class TestUserIdFromJwt:
    def test_extracts_user_id(self) -> None:
        assert _user_id_from_jwt(TEST_JWT) == 198910275


class TestGetCourses:
    def test_extracts_course_fields(self) -> None:
        client = DuolingoClient(TEST_JWT)
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
