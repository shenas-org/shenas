"""Tile source -- syncs device, location, and state data from Tile Bluetooth trackers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Any

from shenas_plugins.core.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source


class TileSource(Source):
    name = "tile"
    display_name = "Tile"
    primary_table = "tile_locations"
    description = (
        "Syncs device info, location history, and battery/connectivity state "
        "from Tile Bluetooth trackers.\n\n"
        "Authenticates via email and password for your Tile account."
    )

    @dataclass
    class Auth(SourceAuth):
        tokens: (
            Annotated[
                str | None,
                Field(db_type="VARCHAR", description="JSON blob of Tile credentials and session", category="secret"),
            ]
            | None
        ) = None

    auth_instructions = (
        "Log in with the email and password for your Tile account\n(the same credentials you use in the Tile mobile app)."
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "email", "prompt": "Email", "hide": False},
            {"name": "password", "prompt": "Password", "hide": True},
        ]

    def build_client(self) -> Any:
        from shenas_sources.tile.client import TileClient

        row = self.Auth.read_row()
        if not row or not row.get("tokens"):
            msg = "No credentials found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)

        creds = json.loads(row["tokens"])
        client = TileClient(
            creds["email"],
            creds["password"],
            client_uuid=creds.get("client_uuid"),
        )
        client.login()
        return client

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.tile.client import TileClient

        email = (credentials.get("email") or "").strip()
        password = (credentials.get("password") or "").strip()
        if not email or not password:
            msg = "email and password are required"
            raise ValueError(msg)

        client = TileClient(email, password)
        try:
            client.login()
        finally:
            client.close()

        self.Auth.write_row(
            tokens=json.dumps(
                {
                    "email": email,
                    "password": password,
                    "client_uuid": client.client_uuid,
                }
            )
        )

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.tile.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
