"""Tile derived views.

``TileInfo`` is a live DuckDB VIEW joining tiles, tile_locations, and
tile_state into a single denormalized snapshot per active Tile device.
"""

from __future__ import annotations

from typing import Annotated

from app.schema import SOURCES
from app.table import Field
from app.view import DataView


class TileInfo(DataView):
    """Derived per-tile snapshot: live view joining Tiles + TileLocations + TileState.

    Defined as a ``DataView`` (DuckDB VIEW) rather than a transform-populated
    table. Always reads live data -- no transform needed, no stale data risk.
    Each surviving row projects to a ``physical_entity`` entity via the
    statement graph.
    """

    class _Meta:
        name = "tile_info"
        display_name = "Tile Info"
        description = "Live device snapshot for each active Tile (derived view)."
        schema = SOURCES
        pk = ("tile_uuid",)
        entity_type = "physical_entity"
        entity_name_column = "name"
        entity_wikidata_qid = "Q223557"
        entity_projection = {  # noqa: RUF012
            "tile_type": "type",
            "firmware_version": "firmware",
            "hardware_version": "hardware",
            "latitude": "latitude",
            "longitude": "longitude",
            "last_seen_at": "last_seen",
            "battery_level": "battery_level",
            "battery_state": "battery_state",
            "connection_state": "connection_state",
        }

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID", display_name="Tile UUID")] = ""
    name: Annotated[
        str | None, Field(db_type="VARCHAR", description="User-assigned device name", display_name="Device Name")
    ] = None
    tile_type: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Tile product type", display_name="Tile Type"),
    ] = None
    firmware_version: Annotated[
        str | None, Field(db_type="VARCHAR", description="Current firmware version", display_name="Firmware Version")
    ] = None
    hardware_version: Annotated[
        str | None, Field(db_type="VARCHAR", description="Hardware version", display_name="Hardware Version")
    ] = None
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Latest latitude", display_name="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Latest longitude", display_name="Longitude")] = (
        None
    )
    last_seen_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Timestamp of the latest location observation", display_name="Last Seen"),
    ] = None
    battery_level: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Battery level",
            display_name="Battery",
            unit="percent",
            value_range=(0, 100),
        ),
    ] = None
    battery_state: Annotated[
        str | None, Field(db_type="VARCHAR", description="Battery state", display_name="Battery State")
    ] = None
    connection_state: Annotated[
        str | None, Field(db_type="VARCHAR", description="Connection state", display_name="Connection State")
    ] = None
    is_dead: Annotated[
        bool, Field(db_type="BOOLEAN", description="Tile battery depleted", display_name="Dead", db_default="FALSE")
    ] = False

    @classmethod
    def _view_sql(cls) -> str:
        return (
            "WITH latest_loc AS ("
            "  SELECT tile_uuid, latitude, longitude, last_timestamp,"
            "    ROW_NUMBER() OVER (PARTITION BY tile_uuid ORDER BY last_timestamp DESC) AS rn"
            "  FROM sources.tile__tile_locations"
            ") "
            "SELECT t.tile_uuid, t.name, t.tile_type, t.firmware_version, t.hardware_version,"
            "  l.latitude, l.longitude, l.last_timestamp AS last_seen_at,"
            "  s.battery_level, s.battery_state, s.connection_state,"
            "  COALESCE(s.is_dead, FALSE) AS is_dead "
            "FROM sources.tile__tiles t "
            "LEFT JOIN latest_loc l ON l.tile_uuid = t.tile_uuid AND l.rn = 1 "
            "LEFT JOIN sources.tile__tile_state s ON s.tile_uuid = t.tile_uuid AND s._dlt_valid_to IS NULL "
            "WHERE t._dlt_valid_to IS NULL AND COALESCE(s.is_dead, FALSE) = FALSE"
        )


VIEWS: tuple[type[DataView], ...] = (TileInfo,)
