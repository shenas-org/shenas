"""Device identity -- generate and store Ed25519 keypair, register with server."""

from __future__ import annotations

import logging
import platform
import socket
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

log = logging.getLogger("shenas.mesh")

_DEVICE_TABLE = """\
CREATE TABLE IF NOT EXISTS shenas_system.device_identity (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)"""


def _get_or_create_identity() -> dict[str, str]:
    """Get or create the device identity (Ed25519 keypair + device name)."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute(_DEVICE_TABLE)
        row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'private_key'").fetchone()
        if row:
            name_row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'device_name'").fetchone()
            pub_row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'public_key'").fetchone()
            return {
                "private_key": row[0],
                "public_key": pub_row[0] if pub_row else "",
                "device_name": name_row[0] if name_row else socket.gethostname(),
            }

    # Generate new keypair
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    public_pem = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    device_name = f"{platform.node()}"

    with cursor() as cur:
        cur.execute(_DEVICE_TABLE)
        for k, v in [("private_key", private_pem), ("public_key", public_pem), ("device_name", device_name)]:
            cur.execute(
                "INSERT INTO shenas_system.device_identity (key, value) VALUES (?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = ?",
                [k, v, v],
            )

    log.info("Generated device identity: %s", device_name)
    return {"private_key": private_pem, "public_key": public_pem, "device_name": device_name}


def get_device_info() -> dict[str, str]:
    """Return public device info (no private key)."""
    identity = _get_or_create_identity()
    return {
        "device_name": identity["device_name"],
        "public_key": identity["public_key"],
        "device_type": _detect_device_type(),
    }


def _detect_device_type() -> str:
    system = platform.system().lower()
    if system == "android":
        return "mobile"
    if system == "darwin":
        return "desktop"
    if system == "linux":
        return "desktop"
    if system == "windows":
        return "desktop"
    return "unknown"


def register_with_server(server_url: str, token: str) -> dict[str, Any] | None:
    """Register this device with the shenas.net web-api."""
    import httpx

    info = get_device_info()
    try:
        resp = httpx.post(
            f"{server_url}/api/devices",
            json={
                "name": info["device_name"],
                "device_type": info["device_type"],
                "public_key": info["public_key"],
            },
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=10,
        )
        if resp.status_code == 200:
            log.info("Registered device with server: %s", info["device_name"])
            return resp.json()
        log.warning("Device registration failed: %s", resp.text)
    except Exception:
        log.exception("Failed to register device")
    return None
