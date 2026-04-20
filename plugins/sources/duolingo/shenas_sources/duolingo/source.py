"""Duolingo source -- syncs daily XP, course progress, and profile data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class DuolingoSource(Source):
    name = "duolingo"
    display_name = "Duolingo"
    primary_table = "daily_xp"
    entity_types: ClassVar[list[str]] = ["human"]
    description = (
        "Syncs daily XP, course progress, and profile data from Duolingo.\n\n"
        "Duolingo has no official API. This source uses the unofficial REST API "
        "with a JWT token extracted from your browser session."
    )

    @dataclass
    class Config(SourceConfig):
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch on initial sync (unset = source default)",
                ui_widget="text",
                example_value="30",
            ),
        ] = None

    @dataclass
    class Auth(SourceAuth):
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
        from shenas_sources.duolingo.client import DuolingoClient

        row = self.Auth.read_row()
        if not row or not row.get("jwt_token"):
            msg = "No JWT token found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return DuolingoClient(row["jwt_token"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.duolingo.client import DuolingoClient

        jwt = (credentials.get("jwt_token") or "").strip()
        if not jwt:
            msg = "jwt_token is required"
            raise ValueError(msg)
        client = DuolingoClient(jwt)
        try:
            client.get_user()
        finally:
            client.close()
        self.Auth.write_row(jwt_token=jwt)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.duolingo.tables import TABLES, DailyXp

        start = self._lookback_start_date(30)
        return [t.to_resource(client, start_date=start) if t is DailyXp else t.to_resource(client) for t in TABLES]
