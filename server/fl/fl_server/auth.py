"""Client authentication for the FL server.

Clients register with a token and must present it on every API request.
Tokens are stored in a JSON file alongside the weights directory.

For Phase 4, this is token-based auth. mTLS can be added later.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_FILE = Path(".shenas-fl/clients.json")


class ClientRegistry:
    """Manages registered FL clients and their auth tokens."""

    def __init__(self, token_file: Path = _TOKEN_FILE) -> None:
        self._path = token_file
        self._clients: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            import json

            self._clients = json.loads(self._path.read_text())
            logger.info("Loaded %d registered clients", len(self._clients))

    def _save(self) -> None:
        import json

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._clients, indent=2))

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def register(self, client_name: str) -> str:
        """Register a new client. Returns the auth token (shown once)."""
        token = secrets.token_urlsafe(32)
        self._clients[client_name] = {
            "token_hash": self._hash(token),
            "name": client_name,
        }
        self._save()
        logger.info("Registered client: %s", client_name)
        return token

    def verify(self, token: str) -> str | None:
        """Verify a token. Returns the client name if valid, None otherwise."""
        token_hash = self._hash(token)
        for name, info in self._clients.items():
            if info["token_hash"] == token_hash:
                return name
        return None

    def revoke(self, client_name: str) -> bool:
        """Revoke a client's access."""
        if client_name in self._clients:
            del self._clients[client_name]
            self._save()
            return True
        return False

    def list_clients(self) -> list[str]:
        """List all registered client names."""
        return list(self._clients.keys())
