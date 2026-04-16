"""Tile source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``.

- ``Tiles`` is a ``DimensionTable`` (SCD2) keyed on ``tile_uuid``.
  Captures changes to device name, firmware, hardware version, and
  tile type across syncs.
- ``TileLocations`` is an ``EventTable`` keyed on (``tile_uuid``,
  ``last_timestamp``). Each unique location observation per tile
  is stored; merge deduplicates same-timestamp rows.
- ``TileState`` is a ``SnapshotTable`` (SCD2) keyed on ``tile_uuid``.
  Tracks battery level, connection state, and ring state changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.entity import EntityMapTable, EntityType
from app.table import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.tile.client import TileClient


def _to_iso(value: Any) -> str | None:
    """Coerce a Tile timestamp to an ISO-8601 string, or None if missing.

    Tile's API returns timestamps as Unix epoch in **milliseconds**
    (per the upstream pytile reference). dlt cannot coerce a bare int
    to TIMESTAMP, so we convert here. Strings (already ISO) and
    datetime objects pass through.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)) and value > 0:
        # Tile uses milliseconds; treat values past year ~2001 as ms,
        # smaller as seconds (defensive -- shouldn't happen in practice).
        seconds = value / 1000.0 if value > 1_000_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=UTC).isoformat()
    return str(value) or None


class Tiles(DimensionTable):
    """Registered Tile devices. SCD2 captures renames and firmware updates."""

    class _Meta:
        name = "tiles"
        display_name = "Tiles"
        description = "Registered Tile Bluetooth tracker devices."
        pk = ("tile_uuid",)

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID", display_name="Tile UUID")]
    name: Annotated[
        str | None, Field(db_type="VARCHAR", description="User-assigned device name", display_name="Device Name")
    ] = None
    tile_type: Annotated[
        str | None,
        Field(
            db_type="VARCHAR", description="Tile product type (e.g. TILE, SLIM, MATE, PRO, STICKER)", display_name="Tile Type"
        ),
    ] = None
    firmware_version: Annotated[
        str | None, Field(db_type="VARCHAR", description="Current firmware version", display_name="Firmware Version")
    ] = None
    hardware_version: Annotated[
        str | None, Field(db_type="VARCHAR", description="Hardware version", display_name="Hardware Version")
    ] = None

    @classmethod
    def extract(cls, client: TileClient, **_: Any) -> Iterator[dict[str, Any]]:
        for tile in client.get_tiles():
            yield {
                "tile_uuid": tile.get("uuid") or tile.get("tile_uuid") or "",
                "name": tile.get("name"),
                "tile_type": tile.get("tile_type") or tile.get("type"),
                "firmware_version": tile.get("firmware_version"),
                "hardware_version": tile.get("hardware_version"),
            }


class TileLocations(EventTable):
    """Location observations from Tile devices.

    Each sync captures the last known location per tile. The composite PK
    (tile_uuid, last_timestamp) deduplicates: if the tile hasn't moved
    between syncs the same row is merged, but a new position creates a
    new row -- building location history over time.
    """

    class _Meta:
        name = "tile_locations"
        display_name = "Tile Locations"
        description = "Last-known location observations from Tile trackers."
        pk = ("tile_uuid", "last_timestamp")
        time_at = "last_timestamp"

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID", display_name="Tile UUID")]
    last_timestamp: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Timestamp of the location observation", display_name="Last Seen Time"),
    ] = None
    latitude: Annotated[
        float | None, Field(db_type="DOUBLE", description="Latitude in decimal degrees", display_name="Latitude")
    ] = None
    longitude: Annotated[
        float | None, Field(db_type="DOUBLE", description="Longitude in decimal degrees", display_name="Longitude")
    ] = None
    altitude: Annotated[float | None, Field(db_type="DOUBLE", description="Altitude", display_name="Altitude", unit="m")] = (
        None
    )
    is_approximate: Annotated[
        bool | None,
        Field(
            db_type="BOOLEAN",
            description="Whether the location is approximate (community find vs GPS)",
            display_name="Approximate",
        ),
    ] = None

    @classmethod
    def _get(cls, tile: dict[str, Any], key: str) -> Any:
        """Look up *key* in ``last_tile_state`` first, then top-level tile dict."""
        state = tile.get("last_tile_state") or {}
        val = state.get(key)
        if val is not None:
            return val
        return tile.get(key)

    @classmethod
    def extract(cls, client: TileClient, **_: Any) -> Iterator[dict[str, Any]]:
        for tile in client.get_tiles():
            tile_uuid = tile.get("uuid") or tile.get("tile_uuid") or ""
            if not tile_uuid:
                continue
            ts = _to_iso(cls._get(tile, "timestamp"))
            if not ts:
                continue
            yield {
                "tile_uuid": tile_uuid,
                "last_timestamp": ts,
                "latitude": cls._get(tile, "latitude"),
                "longitude": cls._get(tile, "longitude"),
                "altitude": cls._get(tile, "altitude"),
                "is_approximate": cls._get(tile, "is_approximate"),
            }


class TileState(SnapshotTable):
    """Current device state. SCD2 tracks battery, connectivity, and ring changes."""

    class _Meta:
        name = "tile_state"
        display_name = "Tile State"
        description = "Battery level, connection state, and ring state for each Tile."
        pk = ("tile_uuid",)

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID", display_name="Tile UUID")]
    battery_level: Annotated[
        int | None,
        Field(
            db_type="INTEGER", description="Battery level", display_name="Battery Level", unit="percent", value_range=(0, 100)
        ),
    ] = None
    battery_state: Annotated[
        str | None, Field(db_type="VARCHAR", description="Battery state (e.g. OK, LOW, DEAD)", display_name="Battery State")
    ] = None
    connection_state: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Connection state (e.g. CONNECTED, DISCONNECTED, READY)",
            display_name="Connection State",
        ),
    ] = None
    is_dead: Annotated[
        bool, Field(db_type="BOOLEAN", description="Whether the Tile battery is depleted", display_name="Dead")
    ] = False
    ring_state: Annotated[
        str | None, Field(db_type="VARCHAR", description="Ring state (e.g. RINGING, STOPPED)", display_name="Ring State")
    ] = None
    last_tile_state_timestamp: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Timestamp of the last state update", display_name="Last State Update"),
    ] = None

    @classmethod
    def _get(cls, tile: dict[str, Any], key: str) -> Any:
        """Look up *key* in ``last_tile_state`` first, then top-level tile dict."""
        state = tile.get("last_tile_state") or {}
        val = state.get(key)
        if val is not None:
            return val
        return tile.get(key)

    @classmethod
    def extract(cls, client: TileClient, **_: Any) -> Iterator[dict[str, Any]]:
        for tile in client.get_tiles():
            tile_uuid = tile.get("uuid") or tile.get("tile_uuid") or ""
            if not tile_uuid:
                continue
            # connection_state has multiple possible key names
            conn = cls._get(tile, "connection_state_machine_state")
            if conn is None:
                conn = cls._get(tile, "connection_state")
            yield {
                "tile_uuid": tile_uuid,
                "battery_level": cls._get(tile, "battery_level"),
                "battery_state": cls._get(tile, "battery_state"),
                "connection_state": conn,
                "is_dead": bool(cls._get(tile, "is_dead") or False),
                "ring_state": cls._get(tile, "ring_state"),
                "last_tile_state_timestamp": _to_iso(cls._get(tile, "timestamp")),
            }


class TileInfo(EntityMapTable):
    """Derived per-tile snapshot joining Tiles + TileLocations + TileState.

    Populated by the bundled SQL transform, which filters out tiles whose
    ``connection_state`` is ``DISCONNECTED`` or whose ``is_dead`` flag is set.
    Each surviving row is a **would-be** entity: the user decides what real
    entity each physical tile is attached to (key, bag, bike, dog) from the
    plugin's Entities tab.

    Because rows are produced by a transform (not by dlt), the SCD2
    ``_dlt_valid_to`` column is declared explicitly on the dataclass so
    ``Table.ensure()`` creates it and downstream filters (the Entities-tab
    ``WHERE _dlt_valid_to IS NULL`` selector) keep working.
    """

    class _Meta:
        name = "tile_info"
        display_name = "Tile Info"
        description = "Live device snapshot for each active Tile (derived)."
        pk = ("tile_uuid",)
        entity_type = EntityType.default("physical_entity")
        entity_name_column = "name"

    # Statement projection (new graph model). Per-tile attributes land as
    # entities.statements rows so the entity panel can render them without
    # needing a per-plugin resolver.
    entity_type: ClassVar[str] = "physical_entity"
    entity_name_column: ClassVar[str] = "name"
    entity_projection: ClassVar[dict[str, str]] = {
        "tile_type": "tile:type",
        "firmware_version": "tile:firmware",
        "hardware_version": "tile:hardware",
        "latitude": "tile:latitude",
        "longitude": "tile:longitude",
        "last_seen_at": "tile:last_seen",
        "battery_level": "tile:battery_level",
        "battery_state": "tile:battery_state",
        "connection_state": "tile:connection_state",
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
    source: Annotated[
        str,
        Field(db_type="VARCHAR", description="Source plugin that produced the row", db_default="'tile'"),
    ] = "tile"
    _dlt_valid_to: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="SCD2 row close time; NULL = current slice"),
    ] = None

    @classmethod
    def extract(cls, client: TileClient, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        # Populated by the bundled SQL transform, not by dlt. Yield nothing so
        # the dlt sync path is a no-op; the transform fills the table.
        if False:
            yield {}


TABLES: tuple[type[SourceTable], ...] = (Tiles, TileLocations, TileState, TileInfo)
