"""Open-Meteo source -- daily weather and air quality for configured places.

No authentication required. Enable place entities (city, residence) in
the Entities tab; the sync fetches data for each enabled place that has
latitude and longitude. Data available back to 1940 (weather) and
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
        "enabled place entity.\n\n"
        "Uses the ERA5 reanalysis archive (back to 1940) and the CAMS air quality "
        "model. No API key required.\n\n"
        "Enable place entities (cities, residences) in the Entities tab. Each "
        "must have latitude and longitude statements set."
    )

    @dataclass
    class Config(SourceConfig):
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch on initial sync (unset = source default)",
                ui_widget="text",
                example_value="365",
            ),
        ] = None
        entity_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                display_name="Places",
                description="Select places to fetch weather data for",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.openmeteo.client import OpenMeteoClient

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
        return OpenMeteoClient(places)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openmeteo.tables import TABLES

        start = self._lookback_start_date(365)
        return [t.to_resource(client, start_date=start) for t in TABLES]


def _load_enabled_places(entity_uuids: list[str]) -> list[tuple[str, float, float]]:
    """Return ``[(entity_id, latitude, longitude), ...]`` for enabled place entities."""
    from app.entities.places import PlacesWide

    if not entity_uuids:
        return []
    uuid_set = set(entity_uuids)
    rows = PlacesWide.all(where="latitude IS NOT NULL AND longitude IS NOT NULL")
    return [
        (r.entity_id, float(r.latitude), float(r.longitude))  # ty: ignore[invalid-argument-type]
        for r in rows
        if r.entity_id in uuid_set
    ]
