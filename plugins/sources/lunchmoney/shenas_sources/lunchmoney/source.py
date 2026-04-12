"""Lunch Money pipe -- syncs financial data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source


class LunchMoneySource(Source):
    name = "lunchmoney"
    display_name = "Lunch Money"
    primary_table = "transactions"
    description = "Syncs financial data from Lunch Money.\n\nAuthenticates via API key from Lunch Money Settings > Developers."

    @dataclass
    class Auth(SourceAuth):
        api_key: (
            Annotated[str | None, Field(db_type="VARCHAR", description="Lunch Money API key", category="secret")] | None
        ) = None

    auth_instructions = (
        "Enter your Lunch Money API key.\n\nGet your key from: Lunch Money > Settings > Developers > Request new Access Token"
    )

    def build_client(self) -> Any:
        from lunchable import LunchMoney

        row = self.Auth.read_row()
        if not row or not row.get("api_key"):
            msg = "No API key found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return LunchMoney(access_token=row["api_key"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from lunchable import LunchMoney

        api_key = (credentials.get("api_key") or credentials.get("password") or "").strip()
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)
        client = LunchMoney(access_token=api_key)
        client.get_user()  # verify the key works
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.lunchmoney.tables import TABLES

        # Each Table subclass owns its schema, kind, and extract logic.
        # The kind base class drives the dlt write_disposition (events ->
        # merge, dimensions/snapshots -> SCD2, etc.) automatically. The
        # `start_date` context kwarg is forwarded to extract() where it's
        # consumed by the cursor-based / windowed tables that need it.
        return [t.to_resource(client, start_date="90 days ago") for t in TABLES]
