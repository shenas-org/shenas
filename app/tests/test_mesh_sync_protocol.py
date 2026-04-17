"""Unit tests for the libp2p sync protocol.

Verifies request/response shape and deduplication. Two-host transport-level
integration is covered by ``test_mesh_libp2p_host.py``.
"""

from __future__ import annotations

import json

from app.mesh.sync_log import append_event, ensure_sync_tables
from app.mesh.sync_protocol import (
    apply_response,
    build_request,
    build_response,
    make_handler,
)


def _seed(table: str, op: str, key: str, payload: str = "") -> str:
    return append_event(
        table_schema="test",
        table_name=table,
        operation=op,
        row_key=key,
        payload=payload,
    )


def test_build_request_includes_local_events_and_max_ts(patch_db: None) -> None:
    ensure_sync_tables()
    _seed("foo", "INSERT", "k1")
    _seed("foo", "UPDATE", "k1")

    req = build_request("local-device", "peer-A")
    body = json.loads(req)
    assert body["from_device_id"] == "local-device"
    assert body["have_max_ts"] > 0
    assert len(body["events"]) == 2
    assert {e["row_key"] for e in body["events"]} == {"k1"}


def test_build_response_inserts_request_events_and_returns_local(patch_db: None) -> None:
    ensure_sync_tables()
    _seed("local", "INSERT", "L1")
    incoming = {
        "from_device_id": "peer-A",
        "have_max_ts": 0,
        "events": [
            {
                "event_id": "evt-from-peer-1",
                "device_id": "peer-A",
                "table_schema": "test",
                "table_name": "remote",
                "row_key": "R1",
                "operation": "INSERT",
                "payload": "{}",
                "ts": 10,
            }
        ],
    }
    response = build_response(json.dumps(incoming).encode(), "local-device")
    body = json.loads(response)

    assert body["from_device_id"] == "local-device"
    # Response includes our local "L1" event (have_max_ts was 0) plus the
    # peer event we just inserted.
    row_keys = {e["row_key"] for e in body["events"]}
    assert "L1" in row_keys
    assert "R1" in row_keys


def test_apply_response_deduplicates_by_event_id(patch_db: None) -> None:
    ensure_sync_tables()
    incoming_event = {
        "event_id": "evt-X",
        "device_id": "peer-B",
        "table_schema": "test",
        "table_name": "remote",
        "row_key": "X",
        "operation": "INSERT",
        "payload": "{}",
        "ts": 100,
    }
    response_bytes = json.dumps({"from_device_id": "peer-B", "have_max_ts": 0, "events": [incoming_event]}).encode()

    inserted_first = apply_response(response_bytes, "peer-B")
    inserted_second = apply_response(response_bytes, "peer-B")
    assert inserted_first == 1
    assert inserted_second == 0


def test_make_handler_returns_response_bytes(patch_db: None) -> None:
    import asyncio

    ensure_sync_tables()
    handler = make_handler("local-device")
    request = json.dumps({"from_device_id": "peer", "have_max_ts": 0, "events": []}).encode()

    async def go() -> bytes:
        return await handler("peer-id", request)

    out = asyncio.run(go())
    body = json.loads(out)
    assert body["from_device_id"] == "local-device"
    assert "events" in body
