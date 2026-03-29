from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.duolingo.client import DuolingoClient


class TestLogin:
    @patch("shenas_pipes.duolingo.client.httpx.post")
    def test_returns_jwt(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"jwt": "token-abc"}
        mock_post.return_value = mock_resp

        jwt = DuolingoClient.login("user", "pass")
        assert jwt == "token-abc"

    @patch("shenas_pipes.duolingo.client.httpx.post")
    def test_invalid_credentials(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="Invalid credentials"):
            DuolingoClient.login("user", "wrong")

    @patch("shenas_pipes.duolingo.client.httpx.post")
    def test_no_jwt_in_response(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="No JWT token"):
            DuolingoClient.login("user", "pass")


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
