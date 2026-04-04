"""Google Calendar pipe -- syncs events and calendar metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_pipes.core.pipe import Pipe
from shenas_plugins.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field


class GCalendarPipe(Pipe):
    name = "gcalendar"
    display_name = "Google Calendar"
    primary_table = "events"
    description = (
        "Syncs events and calendar metadata from Google Calendar.\n\n"
        "Uses Google OAuth2 with shared credentials from shenas-pipe-core."
    )

    @dataclass
    class Auth(PipeAuth):
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
        from shenas_pipes.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gcalendar",
            ["https://www.googleapis.com/auth/calendar.readonly"],
            "calendar",
            "v3",
            auth_cls=self.Auth,
        )

    def build_client(self) -> Any:
        return self._google_auth().build_client()

    def authenticate(self, credentials: dict[str, str]) -> None:
        self._google_auth().authenticate(credentials)

    def resources(self, client: Any) -> list[Any]:
        from shenas_pipes.gcalendar.source import all_events, calendars

        return [all_events(client), calendars(client)]
