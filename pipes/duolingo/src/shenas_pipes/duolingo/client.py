"""Thin Duolingo API client using httpx (unofficial, reverse-engineered endpoints)."""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://www.duolingo.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class DuolingoClient:
    """HTTP client for the unofficial Duolingo API."""

    def __init__(self, jwt: str) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {jwt}",
                "User-Agent": USER_AGENT,
            },
            timeout=30.0,
        )
        self._user_id: int | None = None

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def login(username: str, password: str) -> str:
        """Authenticate with Duolingo and return a JWT token."""
        resp = httpx.post(
            f"{BASE_URL}/login",
            json={"login": username, "password": password},
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        )
        if resp.status_code == 403:
            raise ValueError("Invalid credentials or account locked")
        resp.raise_for_status()
        jwt = resp.headers.get("jwt")
        if not jwt:
            raise ValueError("No JWT token in login response")
        return jwt

    @property
    def user_id(self) -> int:
        if self._user_id is None:
            data = self.get_user()
            self._user_id = data["id"]
        return self._user_id

    def get_user(self) -> dict[str, Any]:
        """Get the current user's profile data."""
        resp = self._client.get("/api/1/users/show")
        resp.raise_for_status()
        return resp.json()

    def get_xp_summaries(self, start_date: str) -> list[dict[str, Any]]:
        """Get daily XP summaries from a start date.

        Args:
            start_date: ISO date string (YYYY-MM-DD). Duolingo returns
                        summaries from this date to now.
        """
        resp = self._client.get(
            f"/2017-06-30/users/{self.user_id}/xp_summaries",
            params={"startDate": start_date},
        )
        resp.raise_for_status()
        return resp.json().get("summaries", [])

    def get_streak_info(self) -> dict[str, Any]:
        """Get the user's current streak information."""
        data = self.get_user()
        return {
            "streak": data.get("streak_extended_today", data.get("site_streak", 0)),
            "streak_extended_today": data.get("streak_extended_today", False),
            "longest_streak": data.get("longest_streak", 0),
        }

    def get_courses(self) -> list[dict[str, Any]]:
        """Get the user's active language courses."""
        data = self.get_user()
        courses = data.get("courses", [])
        return [
            {
                "language": c.get("title", ""),
                "language_code": c.get("learningLanguage", ""),
                "from_language": c.get("fromLanguage", ""),
                "xp": c.get("xp", 0),
                "crowns": c.get("crowns", 0),
                "level": c.get("level", 0),
            }
            for c in courses
        ]
