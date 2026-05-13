"""Paperclip source -- syncs companies, agents, and projects from a Paperclip instance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import OFFICIAL_API
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source, _clean_auth_error


class PaperclipSource(Source):
    name = "paperclip"
    display_name = "Paperclip"
    primary_table = "paperclip_companies"
    entity_types: ClassVar[list[str]] = ["company"]
    description = (
        "Syncs companies, agents, and projects from a Paperclip instance.\n\n"
        "Authenticate with the API URL and an API key for your Paperclip account."
    )
    access_types = (OFFICIAL_API,)
    default_update_frequency = "R/PT15M"

    @dataclass
    class Auth(SourceAuth):
        tokens: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description='JSON blob: {"api_url": "...", "api_key": "..."}',
                    category="secret",
                ),
            ]
            | None
        ) = None

    auth_instructions = (
        "Enter the base URL of your Paperclip instance and an API key.\n"
        "The API key must belong to an agent that can read company, agent, and project data."
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "api_url", "prompt": "API URL", "hide": False},
            {"name": "api_key", "prompt": "API Key", "hide": True},
        ]

    def build_client(self) -> Any:
        from shenas_sources.paperclip.client import PaperclipClient

        row = self.Auth.read_row()
        if not row or not row.get("tokens"):
            msg = "No credentials found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)

        creds = json.loads(row["tokens"])
        return PaperclipClient(creds["api_url"], creds["api_key"])

    def cleanup_client(self, client: Any) -> None:
        if client is not None:
            client.close()

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.paperclip.client import PaperclipClient

        api_url = (credentials.get("api_url") or "").strip()
        api_key = (credentials.get("api_key") or "").strip()
        if not api_url:
            api_url = "http://127.0.0.1:3100"
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)

        client = PaperclipClient(api_url, api_key)
        try:
            client.get_me()
        except Exception as exc:
            raise ValueError(_clean_auth_error(str(exc))) from exc
        finally:
            client.close()

        self.Auth.write_row(tokens=json.dumps({"api_url": api_url, "api_key": api_key}))

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.paperclip.tables import TABLES

        return [table.to_resource(client) for table in TABLES]
