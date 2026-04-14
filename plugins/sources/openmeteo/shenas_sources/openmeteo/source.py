"""Open-Meteo source -- daily weather and air quality for any location.

No authentication required. Configure latitude and longitude via the
Config tab. Data available back to 1940 (weather) and 2022 (air quality).
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
    entity_types: ClassVar[list[str]] = ["city"]
    default_update_frequency = "R/P1D"
    description = (
        "Daily weather and air quality data from Open-Meteo.\n\n"
        "Uses the ERA5 reanalysis archive (back to 1940) and the CAMS "
        "air quality model. No API key required.\n\n"
        "Set latitude and longitude in the Config tab to choose a location."
    )

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

    def build_client(self) -> Any:
        from shenas_sources.openmeteo.client import OpenMeteoClient

        row = self.Config.read_row()
        if not row or not row.get("latitude") or not row.get("longitude"):
            msg = "Set latitude and longitude in the Config tab."
            raise RuntimeError(msg)
        return OpenMeteoClient(float(row["latitude"]), float(row["longitude"]))

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openmeteo.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
