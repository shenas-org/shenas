"""Thin Duolingo API client using httpx (unofficial, reverse-engineered endpoints)."""

from __future__ import annotations

import json
from base64 import b64decode
from typing import Any

import httpx

BASE_URL = "https://www.duolingo.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

USER_FIELDS = (
    "username,name,streak,totalXp,courses,streakData,currentCourseId,"
    "learningLanguage,fromLanguage,creationDate,xpGoal,achievements,"
    "hasPlus,_achievements,subscriberLevel"
)


def _user_id_from_jwt(jwt: str) -> int:
    """Extract the user ID from the JWT 'sub' claim without verifying the signature."""
    payload = jwt.split(".")[1]
    # Pad base64 if needed
    payload += "=" * (-len(payload) % 4)
    data = json.loads(b64decode(payload))
    return int(data["sub"])


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
        self._user_id = _user_id_from_jwt(jwt)

    def close(self) -> None:
        self._client.close()

    @property
    def user_id(self) -> int:
        return self._user_id

    def get_user(self) -> dict[str, Any]:
        """Get the current user's profile data."""
        resp = self._client.get(
            f"/2017-06-30/users/{self._user_id}",
            params={"fields": USER_FIELDS},
        )
        resp.raise_for_status()
        return resp.json()

    def get_xp_summaries(self, start_date: str) -> list[dict[str, Any]]:
        """Get daily XP summaries from a start date.

        Args:
            start_date: ISO date string (YYYY-MM-DD). Duolingo returns
                        summaries with epoch timestamps for the date field.
        """
        resp = self._client.get(
            f"/2017-06-30/users/{self._user_id}/xp_summaries",
            params={"startDate": start_date},
        )
        resp.raise_for_status()
        return resp.json().get("summaries", [])

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

    def get_achievements(self) -> list[dict[str, Any]]:
        """Get the user's unlocked achievements (badges).

        Returns the raw `achievements` array from the user payload. Each entry
        typically has name, tier, count, unlockTimestamp.
        """
        data = self.get_user()
        return data.get("achievements") or data.get("_achievements") or []

    def get_league(self) -> dict[str, Any] | None:
        """Get the current weekly league standing for the user."""
        try:
            resp = self._client.get(f"/leaderboards/7d9f5dd1-8423-491a-912f-b6c46ed73d09/users/{self._user_id}")
            resp.raise_for_status()
        except httpx.HTTPError:
            return None
        return resp.json()

    def get_following(self) -> list[dict[str, Any]]:
        """Get the list of users this user follows."""
        try:
            resp = self._client.get(f"/2017-06-30/friends/users/{self._user_id}/following")
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        data = resp.json()
        # API has nested under "following" -> "users" or just "users"
        following = data.get("following", data)
        if isinstance(following, dict):
            return following.get("users", []) or []
        return following or []

    def get_followers(self) -> list[dict[str, Any]]:
        """Get the list of users following this user."""
        try:
            resp = self._client.get(f"/2017-06-30/friends/users/{self._user_id}/followers")
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        data = resp.json()
        followers = data.get("followers", data)
        if isinstance(followers, dict):
            return followers.get("users", []) or []
        return followers or []
