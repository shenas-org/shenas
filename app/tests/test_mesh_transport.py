"""Tests for app.mesh.transport -- STUN, local endpoints, peer connect, listener."""

from __future__ import annotations

import socket
import struct
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mesh import transport


def _drive(coro: Any) -> Any:
    """Run an async coroutine that does no real awaits (synchronous internals).

    Avoids constructing a real asyncio event loop, which the sandbox cannot do.
    """
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    msg = "coroutine yielded unexpectedly -- it has real await points"
    raise RuntimeError(msg)


class TestDiscoverPublicEndpoint:
    @pytest.mark.parametrize(
        ("ip", "port"),
        [("203.0.113.5", 54321)],
    )
    def test_parses_xor_mapped_address(self, ip: str, port: int) -> None:
        # Build a STUN response containing XOR-MAPPED-ADDRESS for ip:port.
        magic = 0x2112A442
        xor_port = port ^ 0x2112
        ip_bytes = socket.inet_aton(ip)
        magic_bytes = struct.pack("!I", magic)
        xor_ip = bytes(a ^ b for a, b in zip(ip_bytes, magic_bytes, strict=True))

        # XOR-MAPPED-ADDRESS attribute body: reserved(1) + family(1) + xport(2) + xip(4)
        attr_body = b"\x00\x01" + struct.pack("!H", xor_port) + xor_ip
        attr_header = struct.pack("!HH", 0x0020, len(attr_body))

        stun_header = struct.pack("!HHI", 0x0101, len(attr_body) + 4, magic) + b"\x00" * 12
        response = stun_header + attr_header + attr_body

        sock_inst = MagicMock()
        sock_inst.recvfrom.return_value = (response, ("stun.l.google.com", 19302))
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(transport.discover_public_endpoint())
        assert result is not None
        assert result["address"] == f"{ip}:{port}"
        assert result["type"] == "stun"

    def test_returns_none_on_failure(self) -> None:
        sock_inst = MagicMock()
        sock_inst.recvfrom.side_effect = OSError("timeout")
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(transport.discover_public_endpoint())
        assert result is None


class TestGetLocalEndpoints:
    def test_filters_loopback(self) -> None:
        with (
            patch("socket.gethostname", return_value="host"),
            patch(
                "socket.getaddrinfo",
                return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0)),
                    (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.42", 0)),
                ],
            ),
        ):
            eps = transport.get_local_endpoints()
        assert len(eps) == 1
        assert eps[0]["address"] == "192.168.1.42:7281"
        assert eps[0]["type"] == "direct"

    def test_handles_failure(self) -> None:
        with patch("socket.gethostname", side_effect=OSError("nope")):
            assert transport.get_local_endpoints() == []


class TestRefreshEndpoints:
    def test_no_endpoints_skips_put(self) -> None:
        with (
            patch("app.mesh.transport.get_local_endpoints", return_value=[]),
            patch("app.mesh.transport.discover_public_endpoint", new=AsyncMock(return_value=None)),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            _drive(
                transport.refresh_endpoints("https://srv", "dev-1", "tok"),
            )
        mock_client_cls.assert_not_called()

    def test_puts_endpoints(self) -> None:
        async def _run() -> None:
            mock_client = AsyncMock()
            mock_client.put = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "app.mesh.transport.get_local_endpoints",
                    return_value=[{"address": "10.0.0.1:7281", "type": "direct", "priority": 1}],
                ),
                patch(
                    "app.mesh.transport.discover_public_endpoint",
                    new=AsyncMock(return_value={"address": "203.0.113.1:34567", "type": "stun"}),
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):
                await transport.refresh_endpoints("https://srv", "dev-1", "tok")
            assert mock_client.put.await_count == 1
            call = mock_client.put.await_args
            body = call.kwargs["json"]  # ty: ignore[unresolved-attribute]
            assert len(body["endpoints"]) == 2
            # STUN endpoint gets priority 10
            stun_eps = [e for e in body["endpoints"] if e["type"] == "stun"]
            assert stun_eps[0]["priority"] == 10

        _drive(_run())

    def test_put_failure_is_swallowed(self) -> None:
        async def _run() -> None:
            with (
                patch(
                    "app.mesh.transport.get_local_endpoints",
                    return_value=[{"address": "10.0.0.1:7281", "type": "direct", "priority": 1}],
                ),
                patch("app.mesh.transport.discover_public_endpoint", new=AsyncMock(return_value=None)),
                patch("httpx.AsyncClient", side_effect=RuntimeError("boom")),
            ):
                # Should not raise
                await transport.refresh_endpoints("https://srv", "dev-1", "tok")

        _drive(_run())


class TestTryConnectPeer:
    def test_returns_address_on_pong(self) -> None:
        sock_inst = MagicMock()
        sock_inst.recvfrom.return_value = (b"shenas-pong", ("10.0.0.1", 7281))
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(
                transport.try_connect_peer([{"address": "10.0.0.1:7281", "priority": 5}]),
            )
        assert result == ("10.0.0.1", 7281)

    def test_skips_endpoints_without_port(self) -> None:
        result = _drive(
            transport.try_connect_peer([{"address": "no-port", "priority": 1}]),
        )
        assert result is None

    def test_returns_none_when_all_fail(self) -> None:
        sock_inst = MagicMock()
        sock_inst.recvfrom.side_effect = OSError("nope")
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(
                transport.try_connect_peer([{"address": "10.0.0.1:7281"}]),
            )
        assert result is None

    def test_priority_ordering(self) -> None:
        seen: list[str] = []

        def _make_sock() -> MagicMock:
            s = MagicMock()

            def _send(data: bytes, addr: tuple) -> None:
                seen.append(addr[0])

            s.sendto.side_effect = _send
            s.recvfrom.return_value = (b"shenas-pong", ("10.0.0.2", 7281))
            return s

        with patch("socket.socket", side_effect=lambda *a, **kw: _make_sock()):
            _drive(
                transport.try_connect_peer(
                    [
                        {"address": "10.0.0.1:7281", "priority": 1},
                        {"address": "10.0.0.2:7281", "priority": 10},
                    ],
                ),
            )
        # priority 10 comes first
        assert seen[0] == "10.0.0.2"


class TestSyncWithPeerDirect:
    def test_round_trip(self) -> None:
        peer_events = [{"id": "x"}]
        import json as _json

        sock_inst = MagicMock()
        sock_inst.recvfrom.return_value = (b"shenas-sync:" + _json.dumps(peer_events).encode(), ("10.0.0.1", 7281))
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(
                transport.sync_with_peer_direct(("10.0.0.1", 7281), [{"id": "y"}]),
            )
        assert result == peer_events

    def test_failure_returns_empty(self) -> None:
        sock_inst = MagicMock()
        sock_inst.sendto.side_effect = OSError("nope")
        with patch("socket.socket", return_value=sock_inst):
            result = _drive(
                transport.sync_with_peer_direct(("10.0.0.1", 7281), []),
            )
        assert result == []


class TestSyncListener:
    def test_stop_sets_flag(self) -> None:
        listener = transport.SyncListener(port=8888)
        listener._running = True
        listener.stop()
        assert listener._running is False
