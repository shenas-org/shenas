"""P2P transport -- QUIC connections between devices.

Handles NAT traversal via STUN, direct connections between peers,
and falls back to server relay when direct connection fails.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any

log = logging.getLogger("shenas.mesh.transport")

STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
]


async def discover_public_endpoint() -> dict[str, Any] | None:
    """Discover public IP and port via STUN (RFC 5389).

    Returns {"address": "ip:port", "type": "stun"} or None.
    Uses a minimal STUN binding request -- no external library needed.
    """
    import struct

    # STUN Binding Request: type=0x0001, length=0, magic=0x2112A442, txn=random
    txn_id = __import__("os").urandom(12)
    request = struct.pack("!HHI", 0x0001, 0, 0x2112A442) + txn_id

    for host, port in STUN_SERVERS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.sendto(request, (host, port))
            data, _ = sock.recvfrom(1024)
            sock.close()

            if len(data) < 20:
                continue

            # Parse STUN response -- look for XOR-MAPPED-ADDRESS (0x0020)
            pos = 20  # skip header
            while pos + 4 <= len(data):
                attr_type, attr_len = struct.unpack("!HH", data[pos : pos + 4])
                if attr_type == 0x0020 and attr_len >= 8:
                    # XOR-MAPPED-ADDRESS
                    xor_port = struct.unpack("!H", data[pos + 6 : pos + 8])[0] ^ 0x2112
                    xor_ip_bytes = data[pos + 8 : pos + 12]
                    magic_bytes = struct.pack("!I", 0x2112A442)
                    ip_bytes = bytes(a ^ b for a, b in zip(xor_ip_bytes, magic_bytes, strict=True))
                    ip = socket.inet_ntoa(ip_bytes)
                    return {"address": f"{ip}:{xor_port}", "type": "stun"}
                pos += 4 + attr_len + (4 - attr_len % 4) % 4  # pad to 4 bytes
        except Exception:
            continue
    return None


def get_local_endpoints() -> list[dict[str, str | int]]:
    """Get local network addresses as direct endpoints."""
    endpoints = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = str(info[4][0])
            if not ip.startswith("127."):
                endpoints.append({"address": f"{ip}:7281", "type": "direct", "priority": 1})
    except Exception:
        pass
    return endpoints


async def refresh_endpoints(server_url: str, device_id: str, token: str) -> None:
    """Discover endpoints and update them on the coordination server."""
    import httpx

    endpoints = get_local_endpoints()

    # Try STUN discovery
    stun = await discover_public_endpoint()
    if stun:
        stun["priority"] = 10  # prefer STUN (public) over direct (local)
        endpoints.append(stun)

    if not endpoints:
        return

    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            await client.put(
                f"{server_url}/api/devices/{device_id}/endpoints",
                json={"endpoints": endpoints},
                headers={"Authorization": f"Bearer {token}"},
            )
        log.info("Refreshed %d endpoints for device %s", len(endpoints), device_id)
    except Exception:
        log.exception("Failed to refresh endpoints")


async def try_connect_peer(
    peer_endpoints: list[dict[str, Any]],
) -> tuple[str, int] | None:
    """Try to establish a UDP connection to a peer.

    Attempts endpoints in priority order. Returns (ip, port) on success.
    """
    sorted_eps = sorted(peer_endpoints, key=lambda e: e.get("priority", 0), reverse=True)

    for ep in sorted_eps:
        addr = ep.get("address", "")
        if ":" not in addr:
            continue
        ip, port_str = addr.rsplit(":", 1)
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.sendto(b"shenas-ping", (ip, port))
            data, _ = sock.recvfrom(64)
            sock.close()
            if data == b"shenas-pong":
                log.info("Connected to peer at %s:%d", ip, port)
                return (ip, port)
        except Exception:
            continue
    return None


async def sync_with_peer_direct(
    peer_addr: tuple[str, int],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exchange sync events directly with a peer over UDP.

    Sends our events, receives theirs. Simple request/response protocol.
    For production, this would use QUIC for reliability and multiplexing.
    """
    payload = json.dumps(events).encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        # Send our events
        sock.sendto(b"shenas-sync:" + payload, peer_addr)
        # Receive peer's events
        data, _ = sock.recvfrom(65536)
        if data.startswith(b"shenas-sync:"):
            return json.loads(data[12:])
    except Exception:
        log.exception("Direct sync failed with %s:%d", *peer_addr)
    finally:
        sock.close()
    return []


class SyncListener:
    """UDP listener for incoming sync requests from peers."""

    def __init__(self, port: int = 7281) -> None:
        self.port = port
        self._running = False

    async def start(self) -> None:
        """Start listening for peer sync requests."""
        self._running = True
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.port))
        sock.setblocking(False)
        log.info("Mesh listener started on port %d", self.port)

        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(sock, 65536)
                if data == b"shenas-ping":
                    await loop.sock_sendto(sock, b"shenas-pong", addr)
                elif data.startswith(b"shenas-sync:"):
                    # Receive peer events, respond with ours
                    from app.mesh.relay_sync import apply_remote_events
                    from app.mesh.sync_log import get_events_since

                    apply_remote_events(data[12:].decode())
                    our_events = get_events_since()
                    response = b"shenas-sync:" + json.dumps(our_events).encode()
                    await loop.sock_sendto(sock, response, addr)
            except Exception:
                if self._running:
                    await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False
