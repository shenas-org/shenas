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
        from shenas_sources.openmeteo.client import OpenMeteoClient

        row = self.Config.read_row()
        raw_uuids = (row or {}).get("place_uuids") or ""
        allowed: set[str] | None = {u.strip() for u in raw_uuids.split(",") if u.strip()} or None

        places = _load_place_entities(allowed)
        if not places:
            msg = (
                "No places to sync. Create city / residence / country entities "
                "and add 'latitude' + 'longitude' statements to them, or set "
                "place_uuids in the Config tab to filter."
            )
            raise RuntimeError(msg)
        return OpenMeteoClient(places)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.openmeteo.tables import TABLES

        return [t.to_resource(client) for t in TABLES]


def _load_place_entities(allowed: set[str] | None) -> list[tuple[str, float, float]]:
    """Return ``[(entity_id, latitude, longitude), ...]`` for place entities.

    Reads from ``shenas_system.entities`` (filtered to type IN
    ``city``/``residence``/``country``) and joins with
    ``shenas_system.statements`` for the ``latitude`` + ``longitude``
    properties. Entities missing either coordinate are skipped.

    ``allowed`` is the optional set of entity_ids configured via the
    Config tab; ``None`` means "all places".
    """
    from app.database import cursor

    with cursor() as cur:
        rows = cur.execute(
            """
            SELECT e.uuid,
                   CAST(lat.value AS DOUBLE) AS latitude,
                   CAST(lng.value AS DOUBLE) AS longitude
            FROM shenas_system.entities e
            JOIN shenas_system.statements lat
              ON lat.entity_id = e.uuid
             AND lat.property_id = 'latitude'
             AND lat._dlt_valid_to IS NULL
            JOIN shenas_system.statements lng
              ON lng.entity_id = e.uuid
             AND lng.property_id = 'longitude'
             AND lng._dlt_valid_to IS NULL
            WHERE e.type IN ('city', 'residence', 'country')
            """
        ).fetchall()
    out: list[tuple[str, float, float]] = []
    for uuid, lat, lng in rows:
        if allowed is not None and uuid not in allowed:
            continue
        out.append((uuid, float(lat), float(lng)))
    return out
