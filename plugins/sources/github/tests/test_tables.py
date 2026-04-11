"""Tests for GitHub source tables."""

from __future__ import annotations

from shenas_sources.github.tables import Events, PullRequests, Repositories


class FakeClient:
    """Stub that returns canned API responses."""

    def get_events(self, username: str):
        return [
            {
                "id": "12345",
                "type": "PushEvent",
                "repo": {"name": "user/my-repo"},
                "created_at": "2024-01-15T12:00:00Z",
                "public": True,
            },
            {
                "id": "12346",
                "type": "PullRequestEvent",
                "repo": {"name": "user/other-repo"},
                "created_at": "2024-01-15T13:00:00Z",
                "public": True,
            },
        ]

    def get_repos(self):
        return [
            {
                "id": 100,
                "name": "my-repo",
                "full_name": "user/my-repo",
                "description": "A test repo",
                "language": "Python",
                "private": False,
                "stargazers_count": 42,
                "forks_count": 5,
                "open_issues_count": 3,
                "created_at": "2023-01-01T00:00:00Z",
                "pushed_at": "2024-01-15T12:00:00Z",
            }
        ]

    def search_prs(self, username: str):
        return [
            {
                "id": 200,
                "number": 7,
                "title": "Fix a bug",
                "state": "closed",
                "repository_url": "https://api.github.com/repos/user/my-repo",
                "created_at": "2024-01-10T10:00:00Z",
                "closed_at": "2024-01-12T14:00:00Z",
                "pull_request": {"merged_at": "2024-01-12T14:00:00Z"},
            }
        ]


def test_events_extract() -> None:
    rows = list(Events.extract(FakeClient(), username="user"))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 2
    assert rows[0]["id"] == "12345"
    assert rows[0]["type"] == "PushEvent"
    assert rows[0]["repo_name"] == "user/my-repo"


def test_repositories_extract() -> None:
    rows = list(Repositories.extract(FakeClient()))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 1
    assert rows[0]["name"] == "my-repo"
    assert rows[0]["stargazers_count"] == 42
    assert rows[0]["language"] == "Python"


def test_pull_requests_extract() -> None:
    rows = list(PullRequests.extract(FakeClient(), username="user"))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 1
    assert rows[0]["title"] == "Fix a bug"
    assert rows[0]["state"] == "closed"
    assert rows[0]["merged_at"] == "2024-01-12T14:00:00Z"
    assert rows[0]["repo_full_name"] == "user/my-repo"
