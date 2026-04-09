from unittest.mock import MagicMock

from shenas_sources.tile.tables import TileLocations, Tiles, TileState


def _make_client(tiles: list[dict]) -> MagicMock:
    client = MagicMock()
    client.get_tiles.return_value = tiles
    return client


SAMPLE_TILE = {
    "uuid": "tile-001",
    "name": "Keys",
    "tile_type": "MATE",
    "firmware_version": "01.12.04.0",
    "hardware_version": "02.09",
    "last_tile_state": {
        "timestamp": "2026-04-09T10:30:00Z",
        "latitude": 52.5200,
        "longitude": 13.4050,
        "altitude": 34.0,
        "is_approximate": False,
        "battery_level": 85,
        "battery_state": "OK",
        "connection_state_machine_state": "CONNECTED",
        "is_dead": False,
        "ring_state": "STOPPED",
    },
}


class TestTiles:
    def test_extract_yields_device_info(self) -> None:
        client = _make_client([SAMPLE_TILE])
        rows = list(Tiles.extract(client))
        assert len(rows) == 1
        assert rows[0]["tile_uuid"] == "tile-001"
        assert rows[0]["name"] == "Keys"
        assert rows[0]["tile_type"] == "MATE"
        assert rows[0]["firmware_version"] == "01.12.04.0"

    def test_extract_empty(self) -> None:
        client = _make_client([])
        assert list(Tiles.extract(client)) == []


class TestTileLocations:
    def test_extract_yields_location(self) -> None:
        client = _make_client([SAMPLE_TILE])
        rows = list(TileLocations.extract(client))
        assert len(rows) == 1
        assert rows[0]["tile_uuid"] == "tile-001"
        assert rows[0]["latitude"] == 52.5200
        assert rows[0]["longitude"] == 13.4050
        assert rows[0]["altitude"] == 34.0
        assert rows[0]["last_timestamp"] == "2026-04-09T10:30:00Z"
        assert rows[0]["is_approximate"] is False

    def test_extract_skips_tile_without_timestamp(self) -> None:
        tile = {"uuid": "tile-002", "name": "Wallet"}
        client = _make_client([tile])
        assert list(TileLocations.extract(client)) == []


class TestTileState:
    def test_extract_yields_state(self) -> None:
        client = _make_client([SAMPLE_TILE])
        rows = list(TileState.extract(client))
        assert len(rows) == 1
        assert rows[0]["tile_uuid"] == "tile-001"
        assert rows[0]["battery_level"] == 85
        assert rows[0]["battery_state"] == "OK"
        assert rows[0]["connection_state"] == "CONNECTED"
        assert rows[0]["is_dead"] is False
        assert rows[0]["ring_state"] == "STOPPED"

    def test_extract_handles_missing_state(self) -> None:
        tile = {"uuid": "tile-003", "name": "Backpack"}
        client = _make_client([tile])
        rows = list(TileState.extract(client))
        assert len(rows) == 1
        assert rows[0]["tile_uuid"] == "tile-003"
        assert rows[0]["battery_level"] is None
        assert rows[0]["is_dead"] is False
