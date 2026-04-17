"""Google Calendar source -- syncs events and calendar metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source


class GCalendarSource(Source):
    name = "gcalendar"
    display_name = "Google Calendar"
    primary_table = "events"
    description = (
        "Syncs events and calendar metadata from Google Calendar.\n\n"
        "Uses Google OAuth2 with shared credentials from shenas-source-core."
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

    @property
    def auth_fields(self) -> list:  # No user input -- browser OAuth
        return []

    auth_instructions = "Click Authenticate to sign in with your Google account."

    def _google_auth(self) -> Any:
        from shenas_sources.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gcalendar",
            ["https://www.googleapis.com/auth/calendar.readonly"],
            "calendar",
            "v3",
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
        from shenas_sources.gcalendar.tables import TABLES, fetch_all_events

        # Pre-fetch all raw events once and share between Events + EventAttendees
        # via the `raw_events` context kwarg so we don't call events.list() twice.
        raw_events = fetch_all_events(client)
        return [t.to_resource(client, raw_events=raw_events) for t in TABLES]
