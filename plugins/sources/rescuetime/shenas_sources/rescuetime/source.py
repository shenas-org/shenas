"""RescueTime source -- extracts productivity and screen time data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class RescueTimeSource(Source):
    name = "rescuetime"
    display_name = "RescueTime"
    primary_table = "daily_summary"
    description = (
        "Extracts daily productivity summaries and per-app activity data "
        "from RescueTime.\n\n"
        "Uses the RescueTime Analytics API with an API key for authentication."
    )
    auth_instructions = "Get your API key from https://www.rescuetime.com/anapi/manage.\nClick 'Create a new API key'."

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
        api_key: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="RescueTime API key",
                    category="secret",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        from shenas_sources.rescuetime.client import RescueTimeClient

        row = self.Auth.read_row()
        if not row or not row.get("api_key"):
            msg = "No API key found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return RescueTimeClient(row["api_key"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.rescuetime.client import RescueTimeClient

        api_key = (credentials.get("api_key") or "").strip()
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)
        client = RescueTimeClient(api_key)
        try:
            client.get_daily_summary()
        finally:
            client.close()
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.rescuetime.tables import TABLES

        start = self._lookback_start_date(30)
        return [t.to_resource(client, start_date=start) for t in TABLES]
