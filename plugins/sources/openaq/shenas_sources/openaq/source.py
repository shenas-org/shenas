"""OpenAQ source -- air quality measurements from government monitoring stations.

Requires an API key (free, register at explore.openaq.org). Configure latitude
and longitude to find nearby stations, or set a location_id directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class OpenAQSource(Source):
    name = "openaq"
    display_name = "OpenAQ"
    primary_table = "daily_measurements"
    description = (
        "Air quality data from government monitoring stations via OpenAQ.\n\n"
        "Provides PM2.5, PM10, NO2, SO2, CO, O3, and other pollutants at "
        "hourly resolution, aggregated to daily summaries.\n\n"
        "Requires a free API key from explore.openaq.org."
    )
    auth_instructions = (
        "1. Go to https://explore.openaq.org and create a free account.\n"
        "2. Generate an API key in your account settings.\n"
        "3. Paste the key below."
    )

    @dataclass
    class Auth(SourceAuth):
        api_key: Annotated[
            str | None,
            Field(db_type="VARCHAR", description="OpenAQ API key", category="secret"),
        ] = None

    @dataclass
    class Config(SourceConfig):
        latitude: Annotated[
            float | None,
            Field(db_type="DOUBLE", description="Location latitude (e.g. 59.33 for Stockholm)"),
        ] = None
        longitude: Annotated[
            float | None,
            Field(db_type="DOUBLE", description="Location longitude (e.g. 18.07 for Stockholm)"),
        ] = None
        radius_m: Annotated[
            int | None,
            Field(db_type="INTEGER", description="Search radius in meters (default 25000, max 25000)"),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.openaq.client import OpenAQClient

        auth = self.Auth.read_row()
        if not auth or not auth.get("api_key"):
            msg = "Set your OpenAQ API key in the Auth tab."
            raise RuntimeError(msg)
        cfg = self.Config.read_row()
        if not cfg or not cfg.get("latitude") or not cfg.get("longitude"):
            msg = "Set latitude and longitude in the Config tab."
            raise RuntimeError(msg)
        return OpenAQClient(
            api_key=auth["api_key"],
            latitude=float(cfg["latitude"]),
            longitude=float(cfg["longitude"]),
            radius_m=int(cfg.get("radius_m") or 25000),
        )

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.openaq.client import OpenAQClient

        api_key = credentials.get("api_key", "").strip()
        if not api_key:
            msg = "API key is required."
            raise ValueError(msg)
        client = OpenAQClient(api_key=api_key, latitude=0, longitude=0, radius_m=1000)
        try:
            client.get_parameters()
        except Exception as exc:
            msg = f"Authentication failed: {exc}"
            raise ValueError(msg) from exc
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openaq.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
