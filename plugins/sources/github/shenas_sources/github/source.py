"""GitHub source -- extracts activity, repos, and PRs via the REST API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source


class GithubSource(Source):
    name = "github"
    display_name = "GitHub"
    primary_table = "events"
    description = (
        "Extracts your GitHub activity feed, repositories, and pull requests.\n\n"
        "Uses a personal access token (classic or fine-grained) for "
        "authentication. Events cover the last 90 days of activity."
    )
    auth_instructions = (
        "Create a personal access token at "
        "https://github.com/settings/tokens.\n"
        'Grant at least the "repo" and "read:user" scopes.'
    )

    @dataclass
    class Auth(SourceAuth):
        personal_access_token: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="GitHub personal access token",
                    category="secret",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        from shenas_sources.github.client import GithubClient

        row = self.Auth.read_row()
        if not row or not row.get("personal_access_token"):
            msg = "No token found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return GithubClient(row["personal_access_token"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.github.client import GithubClient

        token = (credentials.get("personal_access_token") or "").strip()
        if not token:
            msg = "personal_access_token is required"
            raise ValueError(msg)
        client = GithubClient(token)
        try:
            client.get_user()
        finally:
            client.close()
        self.Auth.write_row(personal_access_token=token)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.github.tables import TABLES

        username = client.get_user()["login"]
        return [t.to_resource(client, username=username) for t in TABLES]
