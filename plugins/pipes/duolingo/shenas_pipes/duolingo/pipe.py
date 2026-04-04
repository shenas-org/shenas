"""Duolingo pipe -- syncs daily XP, course progress, and profile data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_pipes.core.pipe import Pipe
from shenas_plugins.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field


class DuolingoPipe(Pipe):
    name = "duolingo"
    display_name = "Duolingo"
    primary_table = "daily_xp"
    description = (
        "Syncs daily XP, course progress, and profile data from Duolingo.\n\n"
        "Duolingo has no official API. This pipe uses the unofficial REST API "
        "with a JWT token extracted from your browser session."
    )

    @dataclass
    class Auth(PipeAuth):
        jwt_token: (
            Annotated[str | None, Field(db_type="VARCHAR", description="Browser JWT token", category="secret")] | None
        ) = None

    auth_instructions = (
        "Duolingo blocks programmatic login. Extract a JWT from your browser:\n"
        "\n"
        "  1. Log into duolingo.com\n"
        "  2. Open DevTools (F12) > Console\n"
        "  3. Run:  document.cookie.match(/jwt_token=([^;]+)/)[1]\n"
        "  4. Paste the token below"
    )

    def build_client(self) -> Any:
        from shenas_pipes.duolingo.client import DuolingoClient

        row = self._auth_store.get(self.Auth)
        if not row or not row.get("jwt_token"):
            msg = "No JWT token found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return DuolingoClient(row["jwt_token"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_pipes.duolingo.client import DuolingoClient

        jwt = (credentials.get("jwt_token") or "").strip()
        if not jwt:
            msg = "jwt_token is required"
            raise ValueError(msg)
        client = DuolingoClient(jwt)
        try:
            client.get_user()
        finally:
            client.close()
        self._auth_store.set(self.Auth, jwt_token=jwt)

    def resources(self, client: Any) -> list[Any]:
        from shenas_pipes.duolingo.source import courses, daily_xp, user_profile

        return [daily_xp(client, "30 days ago"), courses(client), user_profile(client)]
