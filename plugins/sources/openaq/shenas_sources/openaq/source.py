"""OpenAQ source -- air quality measurements from government monitoring stations.

Requires an API key (free, register at explore.openaq.org). Configure a
comma-separated list of place-entity UUIDs; each UUID must resolve through
:class:`app.entity.EntityIndex` to a :class:`app.entity.PlaceEntityTable`
row carrying latitude / longitude (and optional ``radius_m``). The sync
fans out across every configured place and tags each row with
``place_uuid``.
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
        "time-series per configured place entity.\n\n"
        "Provides PM2.5, PM10, NO2, SO2, CO, O3, and other pollutants at hourly "
        "resolution, aggregated to daily summaries.\n\n"
        "In the Config tab, set `place_uuids` to a comma-separated list of "
        "place-entity UUIDs. Each must resolve to a PlaceEntityTable row with "
        "latitude / longitude (and optional `radius_m` to cap the search radius).\n\n"
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
        place_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description=(
                    "Comma-separated place-entity UUIDs to sync (each must resolve "
                    "to a PlaceEntityTable row with latitude / longitude; "
                    "`radius_m` on the row caps the per-place search radius)."
                ),
            ),
        ] = None

    def build_client(self) -> Any:
        from app.entity import resolve_place
        from shenas_sources.openaq.client import OpenAQClient

        auth = self.Auth.read_row()
        if not auth or not auth.get("api_key"):
            msg = "Set your OpenAQ API key in the Auth tab."
            raise RuntimeError(msg)

        cfg = self.Config.read_row()
        raw_uuids = (cfg or {}).get("place_uuids") or ""
        uuids = [u.strip() for u in raw_uuids.split(",") if u.strip()]
        if not uuids:
            msg = "Set place_uuids in the Config tab (comma-separated place-entity UUIDs)."
            raise RuntimeError(msg)

        places: list[tuple[str, float, float, int | None]] = []
        missing: list[str] = []
        for uuid in uuids:
            resolved = resolve_place(uuid)
            if resolved is None:
                missing.append(f"{uuid} (not a resolvable place entity)")
                continue
            places.append((resolved.uuid, resolved.latitude, resolved.longitude, resolved.radius_m))
        if missing:
            msg = "Cannot sync: " + "; ".join(missing)
            raise RuntimeError(msg)
        return OpenAQClient(api_key=auth["api_key"], places=places)

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.openaq.client import OpenAQClient

        api_key = (credentials.get("api_key") or "").strip()
        if not api_key:
            msg = "api_key is required"
            raise ValueError(msg)
        # Probe the API with no places -- only validates the key.
        client = OpenAQClient(api_key=api_key, places=[])
        try:
            client.get_parameters()
        finally:
            client.close()
        self.Auth.write_row(api_key=api_key)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openaq.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
