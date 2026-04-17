"""End-to-end test: two LibP2PHost instances exchange a sync request/response."""

from __future__ import annotations

import asyncio

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from app.mesh.libp2p_host import LibP2PHost


def _pem() -> str:
    k = Ed25519PrivateKey.generate()
    return k.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()


def test_two_hosts_roundtrip_sync_protocol() -> None:
    async def run() -> None:
        server = LibP2PHost(_pem(), listen_multiaddrs=("/ip4/127.0.0.1/tcp/0",))
        await server.start()
        try:
            received: list[tuple[str, bytes]] = []

            async def handler(remote_pid: str, req: bytes) -> bytes:
                received.append((remote_pid, req))
                return b"pong:" + req

            server.set_sync_handler(handler)

            client = LibP2PHost(
                _pem(),
                bootstrap_multiaddrs=(server.local_addrs()[0],),
                listen_multiaddrs=("/ip4/127.0.0.1/tcp/0",),
            )
            await client.start()
            try:
                resp = await client.send_sync(server.local_peer_id(), b"hello")
                assert resp == b"pong:hello"
                assert len(received) == 1
                assert received[0][0] == client.local_peer_id()
                assert received[0][1] == b"hello"
            finally:
                await client.stop()
        finally:
            await server.stop()

    asyncio.run(run())


def test_peer_id_is_deterministic_from_pem() -> None:
    async def run() -> None:
        pem = _pem()
        a = LibP2PHost(pem, listen_multiaddrs=("/ip4/127.0.0.1/tcp/0",))
        await a.start()
        pid_a = a.local_peer_id()
        await a.stop()

        b = LibP2PHost(pem, listen_multiaddrs=("/ip4/127.0.0.1/tcp/0",))
        await b.start()
        pid_b = b.local_peer_id()
        await b.stop()

        assert pid_a == pid_b

    asyncio.run(run())
