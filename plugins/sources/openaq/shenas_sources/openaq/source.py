"""OpenAQ source -- air quality measurements from government monitoring stations.

Requires an API key (free, register at explore.openaq.org). Enable place
entities (city, residence) in the Entities tab; the sync fetches data for
each enabled place that has latitude and longitude.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class OpenAQSource(Source):
    name = "openaq"
    display_name = "OpenAQ"
    primary_table = "daily_measurements"
    entity_types: ClassVar[list[str]] = ["place"]
    description = (
        "Air quality data from government monitoring stations via OpenAQ, one "
        "time-series per enabled place entity.\n\n"
        "Provides PM2.5, PM10, NO2, SO2, CO, O3, and other pollutants at hourly "
        "resolution, aggregated to daily summaries.\n\n"
        "Enable place entities (cities, residences) in the Entities tab. Each "
        "must have latitude and longitude statements set.\n\n"
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
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch on initial sync (unset = source default)",
                ui_widget="text",
                example_value="90",
            ),
        ] = None
        entity_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                display_name="Places",
                description="Select places to fetch air quality data for",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.openaq.client import OpenAQClient

        auth = self.Auth.read_row()
        if not auth or not auth.get("api_key"):
            msg = "Set your OpenAQ API key in the Auth tab."
            raise RuntimeError(msg)

        row = self.Config.read_row()
        raw_uuids = (row or {}).get("entity_uuids") or ""
        selected = [u.strip() for u in raw_uuids.split(",") if u.strip()]
        if not selected:
            msg = "No places selected. Choose city or residence entities in the Config tab."
            raise RuntimeError(msg)
        places = _load_enabled_places(selected)
        if not places:
            msg = "Selected places are missing latitude/longitude. Ensure the entities have coordinate statements set."
            raise RuntimeError(msg)
        return OpenAQClient(api_key=auth["api_key"], places=places)

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.openaq.client import OpenAQClient

        api_key = (credentials.get("api_key") or "").strip()
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)
        client = OpenAQClient(api_key=api_key, places=[])
        try:
            client.get_parameters()
        finally:
            client.close()
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openaq.tables import TABLES

        start = self._lookback_start_date(90)
        return [t.to_resource(client, start_date=start) for t in TABLES]


def _load_enabled_places(entity_uuids: list[str]) -> list[tuple[str, float, float, int | None]]:
    """Return ``[(entity_id, latitude, longitude, radius_m), ...]`` for enabled places."""
    from app.entities.places import PlacesWide

    if not entity_uuids:
        return []
    uuid_set = set(entity_uuids)
    rows = PlacesWide.all(where="latitude IS NOT NULL AND longitude IS NOT NULL")
    return [
        (r.entity_id, float(r.latitude), float(r.longitude), int(r.radius_m) if r.radius_m is not None else None)  # ty: ignore[invalid-argument-type]
        for r in rows
        if r.entity_id in uuid_set
    ]
