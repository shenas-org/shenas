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

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.tile.client import TileClient


class Tiles(DimensionTable):
    """Registered Tile devices. SCD2 captures renames and firmware updates."""

    class _Meta:
        name = "tiles"
        display_name = "Tiles"
        description = "Registered Tile Bluetooth tracker devices."
        pk = ("tile_uuid",)

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="User-assigned device name")] = None
    tile_type: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Tile product type (e.g. TILE, SLIM, MATE, PRO, STICKER)"),
    ] = None
    firmware_version: Annotated[str | None, Field(db_type="VARCHAR", description="Current firmware version")] = None
    hardware_version: Annotated[str | None, Field(db_type="VARCHAR", description="Hardware version")] = None

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

    time_at: ClassVar[str] = "last_timestamp"

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID")]
    last_timestamp: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Timestamp of the location observation"),
    ] = None
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Latitude in decimal degrees")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Longitude in decimal degrees")] = None
    altitude: Annotated[float | None, Field(db_type="DOUBLE", description="Altitude", unit="m")] = None
    is_approximate: Annotated[
        bool | None,
        Field(db_type="BOOLEAN", description="Whether the location is approximate (community find vs GPS)"),
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
            ts = cls._get(tile, "timestamp")
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

    tile_uuid: Annotated[str, Field(db_type="VARCHAR", description="Tile device UUID")]
    battery_level: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Battery level", unit="percent", value_range=(0, 100)),
    ] = None
    battery_state: Annotated[str | None, Field(db_type="VARCHAR", description="Battery state (e.g. OK, LOW, DEAD)")] = None
    connection_state: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Connection state (e.g. CONNECTED, DISCONNECTED, READY)"),
    ] = None
    is_dead: Annotated[bool, Field(db_type="BOOLEAN", description="Whether the Tile battery is depleted")] = False
    ring_state: Annotated[str | None, Field(db_type="VARCHAR", description="Ring state (e.g. RINGING, STOPPED)")] = None
    last_tile_state_timestamp: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Timestamp of the last state update"),
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
                "last_tile_state_timestamp": cls._get(tile, "timestamp"),
            }


TABLES: tuple[type[SourceTable], ...] = (Tiles, TileLocations, TileState)
