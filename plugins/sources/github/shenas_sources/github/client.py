"""Thin httpx wrapper for the GitHub REST API."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator

BASE_URL = "https://api.github.com"
_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class GithubClient:
    def __init__(self, token: str) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def get_user(self) -> dict[str, Any]:
        resp = self._client.get("/user")
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, url: str, *, per_page: int = 100) -> Iterator[dict[str, Any]]:
        """Yield items from a paginated GitHub list endpoint."""
        sep = "&" if "?" in url else "?"
        next_url: str | None = f"{url}{sep}per_page={per_page}"
        while next_url:
            resp = self._client.get(next_url)
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, list):
                yield from items
            else:
                yield from items.get("items", [])
            # Follow Link: <...>; rel="next"
            link = resp.headers.get("Link", "")
            m = _LINK_NEXT_RE.search(link)
            next_url = m.group(1) if m else None

    def get_events(self, username: str) -> Iterator[dict[str, Any]]:
        yield from self._paginate(f"/users/{username}/events")

    def get_repos(self) -> Iterator[dict[str, Any]]:
        """Yield all repositories the authenticated user can see.

        GitHub's ``/user/repos`` with ``affiliation=owner,organization_member``
        returns the user's personal repos plus any repo from an org the user
        belongs to, deduplicated on the server side. We avoid repos where the
        user is only a collaborator to keep the list focused on things the
        user or their orgs own.
        """
        yield from self._paginate("/user/repos?affiliation=owner,organization_member&sort=updated")

    def search_prs(self, username: str) -> Iterator[dict[str, Any]]:
        yield from self._paginate(f"/search/issues?q=author:{username}+type:pr+sort:created-desc")
