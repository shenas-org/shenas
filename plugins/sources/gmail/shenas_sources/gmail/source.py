"""Gmail source -- syncs email metadata via Google OAuth2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class GmailSource(Source):
    name = "gmail"
    display_name = "Gmail"
    primary_table = "messages"
    description = (
        "Syncs email metadata from Gmail.\n\n"
        "Uses Google OAuth2 with shared credentials from shenas-source-core. "
        "Authorization URL is passed back to the CLI for browser-based consent."
    )

    @dataclass
    class Auth(SourceAuth):
        token: (
            Annotated[
                str | None,
                Field(db_type="VARCHAR", description="Google OAuth2 credentials (JSON)", category="secret"),
            ]
            | None
        ) = None

    @dataclass
    class Config(SourceConfig):
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch",
                ui_widget="text",
                example_value="90",
            ),
        ] = 90

    @property
    def auth_fields(self) -> list:  # No user input -- browser OAuth
        return []

    auth_instructions = "Click Authenticate to sign in with your Google account."

    def _google_auth(self) -> Any:
        from shenas_sources.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gmail",
            ["https://www.googleapis.com/auth/gmail.readonly"],
            "gmail",
            "v1",
            auth_cls=self.Auth,
        )

    def build_client(self) -> Any:
        return self._google_auth().build_client()

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        return self._google_auth().start_oauth(redirect_uri)

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:
        self._google_auth().complete_oauth(code, state)

    def resources(self, client: Any) -> list[Any]:
        import time

        from shenas_sources.gmail.tables import TABLES, Messages

        days = 90
        query = ""
        try:
            row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
            raw = row.get("lookback_period") if row else None
            days = int(raw) if raw is not None else 90
        except Exception:
            pass
        if days > 0:
            cutoff = int(time.time()) - days * 86400
            query = f"after:{cutoff}"
        self.log.info("Gmail lookback: %d days, query=%r", days, query)
        return [table.to_resource(client, query=query) if table is Messages else table.to_resource(client) for table in TABLES]
