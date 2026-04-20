"""GitHub source tables.

- ``Events`` is an ``EventTable`` from ``/users/{user}/events`` (last 90
  days, max 300 events).
- ``Repositories`` is a ``DimensionTable`` from ``/user/repos`` loaded as
  SCD2 to track star/fork count changes over time.
- ``PullRequests`` is an ``EventTable`` from the search API for PRs
  authored by the user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import AggregateTable, DimensionTable, EventTable, SnapshotTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.github.client import GithubClient


class Events(EventTable):
    """GitHub activity event (push, PR, issue, comment, etc.)."""

    class _Meta:
        name = "events"
        display_name = "Events"
        description = "GitHub activity feed events (last 90 days)."
        pk = ("id",)
        time_at = "created_at"

    id: Annotated[
        str,
        Field(db_type="VARCHAR", description="GitHub event ID", display_name="Event ID"),
    ] = ""
    type: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Event type (PushEvent, PullRequestEvent, ...)",
            display_name="Event Type",
        ),
    ] = ""
    repo_name: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Full repository name (owner/repo)",
            display_name="Repository",
        ),
    ] = ""
    created_at: Annotated[
        str | None,
        Field(
            db_type="TIMESTAMP",
            description="Event timestamp (UTC)",
            display_name="Created At",
        ),
    ] = None
    public: Annotated[
        bool,
        Field(
            db_type="BOOLEAN",
            description="Whether the event is public",
            display_name="Public",
        ),
    ] = True

    @classmethod
    def extract(cls, client: GithubClient, *, username: str = "", **_: Any) -> Iterator[dict[str, Any]]:
        for event in client.get_events(username):
            yield {
                "id": str(event["id"]),
                "type": event.get("type", ""),
                "repo_name": event.get("repo", {}).get("name", ""),
                "created_at": event.get("created_at"),
                "public": event.get("public", True),
            }


class Repositories(DimensionTable):
    """GitHub repository owned by the user, loaded as SCD2. Projects to an entity."""

    class _Meta:
        name = "repositories"
        display_name = "Repositories"
        description = "GitHub repositories owned by the authenticated user."
        pk = ("full_name",)
        entity_type = "repository"
        entity_name_column = "full_name"
        entity_wikidata_qid = "Q1334294"
        entity_projection = {  # noqa: RUF012
            "description": "description",
            "language": "P277",  # programming language
            "private": "private",
            "stargazers_count": "stars",
            "forks_count": "forks",
            "open_issues_count": "open_issues",
            "pushed_at": "pushed_at",
            "created_at": "P571",  # inception
        }

    id: Annotated[
        int,
        Field(
            db_type="BIGINT",
            description="GitHub repository ID",
            display_name="Repository ID",
        ),
    ] = 0
    name: Annotated[
        str,
        Field(db_type="VARCHAR", description="Repository name", display_name="Name"),
    ] = ""
    full_name: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Full name (owner/repo)",
            display_name="Full Name",
        ),
    ] = ""
    description: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Repository description",
            display_name="Description",
        ),
    ] = None
    language: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Primary language", display_name="Language"),
    ] = None
    private: Annotated[
        bool,
        Field(
            db_type="BOOLEAN",
            description="Whether the repository is private",
            display_name="Private",
        ),
    ] = False
    stargazers_count: Annotated[
        int,
        Field(db_type="INTEGER", description="Number of stars", display_name="Stars"),
    ] = 0
    forks_count: Annotated[
        int,
        Field(db_type="INTEGER", description="Number of forks", display_name="Forks"),
    ] = 0
    open_issues_count: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Open issues + PRs",
            display_name="Open Issues",
        ),
    ] = 0
    created_at: Annotated[
        str | None,
        Field(
            db_type="TIMESTAMP",
            description="Repository creation time",
            display_name="Created At",
        ),
    ] = None
    pushed_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Last push time", display_name="Last Push"),
    ] = None

    @classmethod
    def extract(cls, client: GithubClient, **_: Any) -> Iterator[dict[str, Any]]:
        for repo in client.get_repos():
            yield {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "private": repo.get("private", False),
                "stargazers_count": repo.get("stargazers_count", 0),
                "forks_count": repo.get("forks_count", 0),
                "open_issues_count": repo.get("open_issues_count", 0),
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
            }


class PullRequests(EventTable):
    """Pull request authored by the user."""

    class _Meta:
        name = "pull_requests"
        display_name = "Pull Requests"
        description = "Pull requests authored by the authenticated user."
        pk = ("id",)
        time_at = "created_at"

    id: Annotated[
        int,
        Field(db_type="BIGINT", description="GitHub issue/PR ID", display_name="PR ID"),
    ] = 0
    number: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="PR number within the repository",
            display_name="PR Number",
        ),
    ] = 0
    title: Annotated[str, Field(db_type="VARCHAR", description="PR title", display_name="Title")] = ""
    state: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="PR state (open, closed)",
            display_name="State",
        ),
    ] = ""
    repo_full_name: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Full repository name (owner/repo)",
            display_name="Repository",
        ),
    ] = ""
    created_at: Annotated[
        str | None,
        Field(
            db_type="TIMESTAMP",
            description="PR creation time",
            display_name="Created At",
        ),
    ] = None
    closed_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="PR close time", display_name="Closed At"),
    ] = None
    merged_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="PR merge time", display_name="Merged At"),
    ] = None

    @classmethod
    def extract(cls, client: GithubClient, *, username: str = "", **_: Any) -> Iterator[dict[str, Any]]:
        for item in client.search_prs(username):
            repo_url = item.get("repository_url", "")
            repo_name = "/".join(repo_url.rsplit("/", 2)[-2:]) if repo_url else ""
            pr = item.get("pull_request", {})
            yield {
                "id": item["id"],
                "number": item.get("number", 0),
                "title": item.get("title", ""),
                "state": item.get("state", ""),
                "repo_full_name": repo_name,
                "created_at": item.get("created_at"),
                "closed_at": item.get("closed_at"),
                "merged_at": pr.get("merged_at") if pr else None,
            }


class TrafficViews(AggregateTable):
    """Daily page views per repository (last 14 days from GitHub)."""

    class _Meta:
        name = "traffic_views"
        display_name = "Traffic Views"
        description = "Daily page view counts per repository."
        pk = ("repo_full_name", "date")
        time_at = "date"

    repo_full_name: Annotated[str, Field(db_type="VARCHAR", description="Full repository name", display_name="Repository")]
    date: Annotated[str, Field(db_type="DATE", description="Day of the count", display_name="Date")]
    views: Annotated[int, Field(db_type="INTEGER", description="Total page views", display_name="Views")] = 0
    unique_visitors: Annotated[
        int, Field(db_type="INTEGER", description="Unique visitors", display_name="Unique Visitors")
    ] = 0

    @classmethod
    def extract(cls, client: GithubClient, **_: Any) -> Iterator[dict[str, Any]]:
        import httpx

        for repo in client.get_repos():
            full_name = repo["full_name"]
            owner, name = full_name.split("/", 1)
            try:
                data = client.get_traffic_views(owner, name)
            except httpx.HTTPStatusError:
                continue
            for day in data.get("views", []):
                yield {
                    "repo_full_name": full_name,
                    "date": day["timestamp"][:10],
                    "views": day.get("count", 0),
                    "unique_visitors": day.get("uniques", 0),
                }


class TrafficClones(AggregateTable):
    """Daily clone counts per repository (last 14 days from GitHub)."""

    class _Meta:
        name = "traffic_clones"
        display_name = "Traffic Clones"
        description = "Daily git clone counts per repository."
        pk = ("repo_full_name", "date")
        time_at = "date"

    repo_full_name: Annotated[str, Field(db_type="VARCHAR", description="Full repository name", display_name="Repository")]
    date: Annotated[str, Field(db_type="DATE", description="Day of the count", display_name="Date")]
    clones: Annotated[int, Field(db_type="INTEGER", description="Total clones", display_name="Clones")] = 0
    unique_cloners: Annotated[int, Field(db_type="INTEGER", description="Unique cloners", display_name="Unique Cloners")] = 0

    @classmethod
    def extract(cls, client: GithubClient, **_: Any) -> Iterator[dict[str, Any]]:
        import httpx

        for repo in client.get_repos():
            full_name = repo["full_name"]
            owner, name = full_name.split("/", 1)
            try:
                data = client.get_traffic_clones(owner, name)
            except httpx.HTTPStatusError:
                continue
            for day in data.get("clones", []):
                yield {
                    "repo_full_name": full_name,
                    "date": day["timestamp"][:10],
                    "clones": day.get("count", 0),
                    "unique_cloners": day.get("uniques", 0),
                }


class TrafficReferrers(SnapshotTable):
    """Top referral sources per repository (current snapshot, last 14 days)."""

    class _Meta:
        name = "traffic_referrers"
        display_name = "Traffic Referrers"
        description = "Top 10 referral sources per repository."
        pk = ("repo_full_name", "referrer")

    repo_full_name: Annotated[str, Field(db_type="VARCHAR", description="Full repository name", display_name="Repository")]
    referrer: Annotated[str, Field(db_type="VARCHAR", description="Referrer domain or source", display_name="Referrer")]
    views: Annotated[int, Field(db_type="INTEGER", description="Views from this referrer", display_name="Views")] = 0
    unique_visitors: Annotated[
        int, Field(db_type="INTEGER", description="Unique visitors from this referrer", display_name="Unique Visitors")
    ] = 0

    @classmethod
    def extract(cls, client: GithubClient, **_: Any) -> Iterator[dict[str, Any]]:
        import httpx

        for repo in client.get_repos():
            full_name = repo["full_name"]
            owner, name = full_name.split("/", 1)
            try:
                referrers = client.get_traffic_referrers(owner, name)
            except httpx.HTTPStatusError:
                continue
            for ref in referrers:
                yield {
                    "repo_full_name": full_name,
                    "referrer": ref.get("referrer", ""),
                    "views": ref.get("count", 0),
                    "unique_visitors": ref.get("uniques", 0),
                }


class TrafficPaths(SnapshotTable):
    """Top content paths per repository (current snapshot, last 14 days)."""

    class _Meta:
        name = "traffic_paths"
        display_name = "Traffic Paths"
        description = "Top 10 popular content paths per repository."
        pk = ("repo_full_name", "path")

    repo_full_name: Annotated[str, Field(db_type="VARCHAR", description="Full repository name", display_name="Repository")]
    path: Annotated[str, Field(db_type="VARCHAR", description="Content path (e.g. /readme)", display_name="Path")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Page title", display_name="Title")] = None
    views: Annotated[int, Field(db_type="INTEGER", description="Views of this path", display_name="Views")] = 0
    unique_visitors: Annotated[
        int, Field(db_type="INTEGER", description="Unique visitors to this path", display_name="Unique Visitors")
    ] = 0

    @classmethod
    def extract(cls, client: GithubClient, **_: Any) -> Iterator[dict[str, Any]]:
        import httpx

        for repo in client.get_repos():
            full_name = repo["full_name"]
            owner, name = full_name.split("/", 1)
            try:
                paths = client.get_traffic_paths(owner, name)
            except httpx.HTTPStatusError:
                continue
            for p in paths:
                yield {
                    "repo_full_name": full_name,
                    "path": p.get("path", ""),
                    "title": p.get("title"),
                    "views": p.get("count", 0),
                    "unique_visitors": p.get("uniques", 0),
                }


TABLES: tuple[type[SourceTable], ...] = (
    Events,
    Repositories,
    PullRequests,
    TrafficViews,
    TrafficClones,
    TrafficReferrers,
    TrafficPaths,
)
