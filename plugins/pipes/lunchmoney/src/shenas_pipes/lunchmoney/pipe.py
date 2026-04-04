"""Lunch Money pipe -- syncs financial data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_pipes.core.abc import Pipe
from shenas_pipes.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field


class LunchMoneyPipe(Pipe):
    name = "lunchmoney"
    display_name = "Lunch Money"
    description = "Syncs financial data from Lunch Money.\n\nAuthenticates via API key from Lunch Money Settings > Developers."

    @dataclass
    class Auth(PipeAuth):
        api_key: (
            Annotated[str | None, Field(db_type="VARCHAR", description="Lunch Money API key", category="secret")] | None
        ) = None

    auth_instructions = (
        "Enter your Lunch Money API key.\n\nGet your key from: Lunch Money > Settings > Developers > Request new Access Token"
    )

    def build_client(self) -> Any:
        from lunchable import LunchMoney

        row = self._auth_store.get(self.Auth)
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
        self._auth_store.set(self.Auth, api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_pipes.lunchmoney.source import (
            assets,
            budgets,
            categories,
            plaid_accounts,
            recurring_items,
            tags,
            transactions,
        )

        return [
            transactions(client, "90 days ago"),
            categories(client),
            tags(client),
            budgets(client, "90 days ago"),
            recurring_items(client),
            assets(client),
            plaid_accounts(client),
        ]
