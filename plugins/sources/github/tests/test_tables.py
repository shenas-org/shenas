"""Tests for GitHub source tables."""

from shenas_sources.github.tables import (
    Events,
    PullRequests,
    Repositories,
    TrafficClones,
    TrafficPaths,
    TrafficReferrers,
    TrafficViews,
)


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

    def get_traffic_views(self, owner: str, repo: str):
        return {
            "count": 150,
            "uniques": 20,
            "views": [
                {"timestamp": "2024-01-14T00:00:00Z", "count": 80, "uniques": 12},
                {"timestamp": "2024-01-15T00:00:00Z", "count": 70, "uniques": 8},
            ],
        }

    def get_traffic_clones(self, owner: str, repo: str):
        return {
            "count": 10,
            "uniques": 5,
            "clones": [
                {"timestamp": "2024-01-14T00:00:00Z", "count": 6, "uniques": 3},
                {"timestamp": "2024-01-15T00:00:00Z", "count": 4, "uniques": 2},
            ],
        }

    def get_traffic_referrers(self, owner: str, repo: str):
        return [
            {"referrer": "Google", "count": 50, "uniques": 10},
            {"referrer": "GitHub", "count": 30, "uniques": 8},
        ]

    def get_traffic_paths(self, owner: str, repo: str):
        return [
            {"path": "/user/my-repo", "title": "my-repo", "count": 100, "uniques": 15},
            {"path": "/user/my-repo/readme", "title": "README", "count": 40, "uniques": 10},
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


def test_traffic_views_extract() -> None:
    rows = list(TrafficViews.extract(FakeClient()))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 2
    assert rows[0]["repo_full_name"] == "user/my-repo"
    assert rows[0]["date"] == "2024-01-14"
    assert rows[0]["views"] == 80
    assert rows[0]["unique_visitors"] == 12


def test_traffic_clones_extract() -> None:
    rows = list(TrafficClones.extract(FakeClient()))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 2
    assert rows[0]["date"] == "2024-01-14"
    assert rows[0]["clones"] == 6
    assert rows[0]["unique_cloners"] == 3


def test_traffic_referrers_extract() -> None:
    rows = list(TrafficReferrers.extract(FakeClient()))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 2
    assert rows[0]["referrer"] == "Google"
    assert rows[0]["views"] == 50
    assert rows[1]["referrer"] == "GitHub"


def test_traffic_paths_extract() -> None:
    rows = list(TrafficPaths.extract(FakeClient()))  # ty: ignore[invalid-argument-type]
    assert len(rows) == 2
    assert rows[0]["path"] == "/user/my-repo"
    assert rows[0]["title"] == "my-repo"
    assert rows[0]["views"] == 100
    assert rows[1]["unique_visitors"] == 10
