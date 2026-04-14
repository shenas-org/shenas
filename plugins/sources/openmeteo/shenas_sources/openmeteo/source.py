"""Open-Meteo source -- daily weather and air quality for N configured places.

No authentication required. Configure a comma-separated list of place-entity
UUIDs via the Config tab; each UUID must resolve through
:class:`app.entity.EntityIndex` to a source-contributed
:class:`app.entity.PlaceEntityTable` row carrying ``latitude`` and
``longitude``. The sync fans out across every configured place and tags
each row with ``place_uuid``. Data available back to 1940 (weather) and
2022 (air quality).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class OpenMeteoSource(Source):
    name = "openmeteo"
    display_name = "Open-Meteo"
    primary_table = "daily_weather"
    entity_types: ClassVar[list[str]] = ["place"]
    default_update_frequency = "R/P1D"
    description = (
        "Daily weather and air quality data from Open-Meteo, one time-series per "
        "configured place entity.\n\n"
        "Uses the ERA5 reanalysis archive (back to 1940) and the CAMS air quality "
        "model. No API key required.\n\n"
        "In the Config tab, set `place_uuids` to a comma-separated list of "
        "place-entity UUIDs. Each must resolve (via the entity index) to a "
        "source-contributed PlaceEntityTable row with latitude / longitude set."
    )

    @dataclass
    class Config(SourceConfig):
        place_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description=(
                    "Comma-separated place-entity UUIDs to sync (each must resolve "
                    "to a PlaceEntityTable row with latitude / longitude)."
                ),
            ),
        ] = None

    def build_client(self) -> Any:
        from app.entity import resolve_place
        from shenas_sources.openmeteo.client import OpenMeteoClient

        row = self.Config.read_row()
        raw_uuids = (row or {}).get("place_uuids") or ""
        uuids = [u.strip() for u in raw_uuids.split(",") if u.strip()]
        if not uuids:
            msg = "Set place_uuids in the Config tab (comma-separated place-entity UUIDs)."
            raise RuntimeError(msg)

        places: list[tuple[str, float, float]] = []
        missing: list[str] = []
        for uuid in uuids:
            resolved = resolve_place(uuid)
            if resolved is None:
                missing.append(f"{uuid} (not a resolvable place entity)")
                continue
            places.append((resolved.uuid, resolved.latitude, resolved.longitude))
        if missing:
            msg = "Cannot sync: " + "; ".join(missing)
            raise RuntimeError(msg)
        return OpenMeteoClient(places)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openmeteo.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
