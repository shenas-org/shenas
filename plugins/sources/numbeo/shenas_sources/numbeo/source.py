"""Numbeo source -- city-level cost of living, safety, and quality of life.

Requires a paid API key from numbeo.com/api. Configure one or more cities
in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class NumbeoSource(Source):
    name = "numbeo"
    display_name = "Numbeo"
    primary_table = "city_indices"
    description = (
        "City-level cost of living, safety, healthcare, pollution, traffic, "
        "and quality of life data from Numbeo.\n\n"
        "Covers 9000+ cities worldwide. Requires a Numbeo API key.\n\n"
        "Set your API key in the Auth tab and list cities in the Config tab."
    )
    auth_instructions = (
        "1. Go to https://www.numbeo.com/api/ and request API access.\n"
        "2. Once approved, find your API key in your account.\n"
        "3. Paste the key below."
    )

    @dataclass
    class Auth(SourceAuth):
        api_key: Annotated[
            str | None,
            Field(db_type="VARCHAR", description="Numbeo API key", category="secret"),
        ] = None

    @dataclass
    class Config(SourceConfig):
        cities: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description="Comma-separated city names (e.g. Berlin,Stockholm,Amsterdam)",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.numbeo.client import NumbeoClient

        auth = self.Auth.read_row()
        if not auth or not auth.get("api_key"):
            msg = "Set your Numbeo API key in the Auth tab."
            raise RuntimeError(msg)
        cfg = self.Config.read_row()
        if not cfg or not cfg.get("cities"):
            msg = "Set city names in the Config tab (e.g. Berlin,Stockholm)."
            raise RuntimeError(msg)
        cities = [c.strip() for c in cfg["cities"].split(",") if c.strip()]
        return NumbeoClient(api_key=auth["api_key"], cities=cities)

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.numbeo.client import NumbeoClient

        api_key = (credentials.get("api_key") or "").strip()
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)
        client = NumbeoClient(api_key=api_key, cities=[])
        try:
            client.validate_key()
        finally:
            client.close()
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.numbeo.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
