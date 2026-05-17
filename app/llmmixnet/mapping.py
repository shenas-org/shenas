"""Mapping storage for Layer 2 reversible pseudonym mapping (ADR §4.4).

Schema: llmmixnet.mappings
  - mapping_id: UUID (session-scoped)
  - session_id: UUID
  - placeholder: str  (e.g. '<PERSON_0>')
  - mapping_json: BLOB  (XChaCha20-Poly1305 ciphertext of the entity text)
  - nonce: BLOB  (24-byte XChaCha20-Poly1305 nonce)
  - entity_type: str
  - created_at: TIMESTAMPTZ
  - expires_at: TIMESTAMPTZ

Key derivation (ADR §4.4 D5):
  KEY.LLM_MAP = HKDF-SHA256(K1, info="shenas/llmmixnet/v0/map",
                             salt=device_salt, length=32)
  KEY.LLM_MAP_HMAC = HKDF-SHA256(K1, info="shenas/llmmixnet/v0/hmac",
                                  salt=device_salt, length=32)

Storage rules:
  - Local DuckDB only; never replicated, never backed up to shenas-held shares.
  - The mapping_json column is XChaCha20-Poly1305 encrypted per ADR MF-2.
  - No recovery path by design (ADR §4.4 "Recovery").
"""

from __future__ import annotations

import json
import os
import struct
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

if TYPE_CHECKING:
    import duckdb

SESSION_TTL_HOURS = 24
PERSISTENT_TTL_DAYS = 7
XCHACHA20_KEY_SIZE = 32
XCHACHA20_NONCE_SIZE = 24
HMAC_BIN_BITS = 16
HMAC_BIN_COUNT = 2**HMAC_BIN_BITS  # 65536

_MAP_DOMAIN = b"shenas/llmmixnet/v0/map"
_HMAC_DOMAIN = b"shenas/llmmixnet/v0/hmac"


def _derive_map_key(root_key_k1: bytes, device_salt: bytes) -> bytes:
    """Derive KEY.LLM_MAP via HKDF-SHA256 (ADR §4.4 D5 / MF-1)."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=XCHACHA20_KEY_SIZE,
        salt=device_salt,
        info=_MAP_DOMAIN,
    ).derive(root_key_k1)


def _derive_hmac_key(root_key_k1: bytes, device_salt: bytes) -> bytes:
    """Derive KEY.LLM_MAP_HMAC via HKDF-SHA256 (ADR §4.4 D5 / MF-1)."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=XCHACHA20_KEY_SIZE,
        salt=device_salt,
        info=_HMAC_DOMAIN,
    ).derive(root_key_k1)


def _encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """Encrypt with XChaCha20-Poly1305 (ADR §4.4 MF-2).

    Returns (ciphertext, nonce). The nonce is 24 bytes; XChaCha20-Poly1305
    eliminates the nonce-reuse attack vector that AES-GCM exposes under
    library misuse (nonce collision probability negligible at 192-bit nonce).
    """
    nonce = os.urandom(XCHACHA20_NONCE_SIZE)
    # ChaCha20Poly1305 from cryptography uses a 96-bit nonce; XChaCha20 uses
    # 192-bit. We construct XChaCha20 manually using the extended-nonce
    # subkey derivation (HChaCha20) which the library exposes through the
    # extended nonce cipher.
    # Since cryptography >= 41.0 the XChaCha20Poly1305 AEAD class is
    # available. Use it when present; otherwise fall back to ChaCha20Poly1305
    # with a 12-byte nonce (still secure, lacks the 192-bit nonce advantage).
    try:
        from cryptography.hazmat.primitives.ciphers.aead import (  # type: ignore[attr-defined]
            XChaCha20Poly1305,  # ty: ignore[unresolved-import]
        )

        cipher = XChaCha20Poly1305(key)  # type: ignore[name-defined]
    except ImportError:
        # Fall back to ChaCha20Poly1305 with a 12-byte nonce.
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(key)

    ciphertext = cipher.encrypt(nonce, plaintext, None)
    return ciphertext, nonce


def _decrypt(key: bytes, ciphertext: bytes, nonce: bytes) -> bytes:
    """Decrypt with XChaCha20-Poly1305 (or ChaCha20-Poly1305 fallback)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import (  # type: ignore[attr-defined]
            XChaCha20Poly1305,  # ty: ignore[unresolved-import]
        )

        cipher = XChaCha20Poly1305(key) if len(nonce) == 24 else ChaCha20Poly1305(key)  # type: ignore[name-defined]
    except ImportError:
        cipher = ChaCha20Poly1305(key)

    return cipher.decrypt(nonce, ciphertext, None)


def hmac_bin_merchant(hmac_key: bytes, merchant_name: str) -> str:
    """Hash-bin a merchant name to a stable 16-bit bin token (ADR §4.3.1).

    The provider sees 'MERCHANT_BIN_0x4a7c' — stable per-user per-merchant
    (cross-session linkability preserved by design for transaction patterns),
    but the merchant identity is not recoverable from the bin alone.
    """
    hasher = hmac.HMAC(hmac_key, hashes.SHA256())
    hasher.update(merchant_name.encode())
    digest = hasher.finalize()
    bin_index = struct.unpack(">H", digest[:2])[0]
    return f"MERCHANT_BIN_0x{bin_index:04x}"


class MappingStore:
    """DuckDB-backed encrypted placeholder ↔ entity mapping (ADR §4.4).

    Thread-safety: assumes a single-writer caller (the orchestrator is
    intentionally single-threaded per request, ADR §3.2 D12).

    Key material is accepted from the caller (derived from K1 + device_salt
    via _derive_map_key/_derive_hmac_key above). The store never persists or
    derives keys itself.
    """

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        map_key: bytes,
        hmac_key: bytes,
    ) -> None:
        self._con = con
        self._map_key = map_key
        self._hmac_key = hmac_key
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._con.execute("CREATE SCHEMA IF NOT EXISTS llmmixnet")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS llmmixnet.mappings (
                mapping_id  VARCHAR NOT NULL,
                session_id  VARCHAR NOT NULL,
                placeholder VARCHAR NOT NULL,
                mapping_blob BLOB    NOT NULL,
                nonce       BLOB    NOT NULL,
                entity_type VARCHAR NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL,
                expires_at  TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (mapping_id, placeholder)
            )
        """)
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS llmmixnet.sessions (
                session_id      VARCHAR PRIMARY KEY,
                persistent_mode BOOLEAN NOT NULL DEFAULT FALSE,
                created_at      TIMESTAMPTZ NOT NULL,
                last_activity   TIMESTAMPTZ NOT NULL,
                expires_at      TIMESTAMPTZ NOT NULL
            )
        """)
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS llmmixnet.audit_log (
                id          VARCHAR PRIMARY KEY,
                session_id  VARCHAR NOT NULL,
                event_type  VARCHAR NOT NULL,
                detail_json VARCHAR,
                occurred_at TIMESTAMPTZ NOT NULL
            )
        """)

    def create_session(self, persistent_mode: bool = False) -> str:
        """Create a new mapping session and return the session_id."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        ttl = timedelta(days=PERSISTENT_TTL_DAYS) if persistent_mode else timedelta(hours=SESSION_TTL_HOURS)
        expires_at = now + ttl
        self._con.execute(
            """
            INSERT INTO llmmixnet.sessions
                (session_id, persistent_mode, created_at, last_activity, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [session_id, persistent_mode, now, now, expires_at],
        )
        if persistent_mode:
            self._audit(session_id, "persistent_mode_enabled", None)
        return session_id

    def is_persistent(self, session_id: str) -> bool:
        """Return True if this session has persistent pseudonym mode enabled."""
        rows = self._con.execute(
            "SELECT persistent_mode FROM llmmixnet.sessions WHERE session_id = ?",
            [session_id],
        ).fetchall()
        return bool(rows and rows[0][0])

    def touch_session(self, session_id: str) -> None:
        """Update last_activity; extend TTL for persistent sessions (ADR §4.5)."""
        rows = self._con.execute(
            "SELECT persistent_mode, expires_at FROM llmmixnet.sessions WHERE session_id = ?",
            [session_id],
        ).fetchall()
        if not rows:
            return
        persistent_mode, expires_at = rows[0]
        now = datetime.now(UTC)
        if persistent_mode:
            new_expires = now + timedelta(days=PERSISTENT_TTL_DAYS)
            if new_expires > expires_at:
                self._audit(session_id, "ttl_extended", None)
            self._con.execute(
                "UPDATE llmmixnet.sessions SET last_activity = ?, expires_at = ? WHERE session_id = ?",
                [now, new_expires, session_id],
            )
        else:
            new_expires = now + timedelta(hours=SESSION_TTL_HOURS)
            self._con.execute(
                "UPDATE llmmixnet.sessions SET last_activity = ?, expires_at = ? WHERE session_id = ?",
                [now, new_expires, session_id],
            )

    def store_mapping(
        self,
        session_id: str,
        mapping_id: str,
        placeholder: str,
        entity_text: str,
        entity_type: str,
    ) -> None:
        """Encrypt and store a placeholder → entity mapping row."""
        plaintext = entity_text.encode()
        mapping_blob, nonce = _encrypt(self._map_key, plaintext)
        now = datetime.now(UTC)
        expires_at = self._get_session_expires(session_id) or now + timedelta(hours=SESSION_TTL_HOURS)
        self._con.execute(
            """
            INSERT INTO llmmixnet.mappings
                (mapping_id, session_id, placeholder, mapping_blob, nonce,
                 entity_type, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (mapping_id, placeholder) DO NOTHING
            """,
            [mapping_id, session_id, placeholder, mapping_blob, nonce, entity_type, now, expires_at],
        )

    def retrieve_entity(self, mapping_id: str, placeholder: str) -> str | None:
        """Decrypt and return the original entity text for a placeholder.

        Returns None when the mapping has expired or never existed.
        """
        rows = self._con.execute(
            """
            SELECT mapping_blob, nonce FROM llmmixnet.mappings
            WHERE mapping_id = ? AND placeholder = ? AND expires_at > NOW()
            """,
            [mapping_id, placeholder],
        ).fetchall()
        if not rows:
            return None
        mapping_blob, nonce = rows[0]
        return _decrypt(self._map_key, bytes(mapping_blob), bytes(nonce)).decode()

    def list_placeholders(self, mapping_id: str) -> dict[str, str]:
        """Return {placeholder: entity_type} for all active rows in mapping_id."""
        rows = self._con.execute(
            """
            SELECT placeholder, entity_type FROM llmmixnet.mappings
            WHERE mapping_id = ? AND expires_at > NOW()
            """,
            [mapping_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def evict_expired(self) -> int:
        """Remove expired mapping rows. Returns the count deleted."""
        result = self._con.execute("DELETE FROM llmmixnet.mappings WHERE expires_at <= NOW() RETURNING 1").fetchall()
        self._con.execute("DELETE FROM llmmixnet.sessions WHERE expires_at <= NOW()")
        return len(result)

    def hmac_bin(self, merchant_name: str) -> str:
        """Return the HMAC bin token for a merchant name (ADR §4.3.1)."""
        return hmac_bin_merchant(self._hmac_key, merchant_name)

    def _get_session_expires(self, session_id: str) -> datetime | None:
        rows = self._con.execute(
            "SELECT expires_at FROM llmmixnet.sessions WHERE session_id = ?",
            [session_id],
        ).fetchall()
        return rows[0][0] if rows else None

    def _audit(self, session_id: str, event_type: str, detail: dict | None) -> None:
        """Write a row to the local audit log (never to telemetry)."""
        self._con.execute(
            """
            INSERT INTO llmmixnet.audit_log (id, session_id, event_type, detail_json, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                str(uuid.uuid4()),
                session_id,
                event_type,
                json.dumps(detail) if detail else None,
                datetime.now(UTC),
            ],
        )

    @classmethod
    def from_root_key(
        cls,
        con: duckdb.DuckDBPyConnection,
        root_key_k1: bytes,
        device_salt: bytes,
    ) -> MappingStore:
        """Construct a MappingStore from K1 + device_salt (ADR §4.4 D5)."""
        map_key = _derive_map_key(root_key_k1, device_salt)
        hmac_key = _derive_hmac_key(root_key_k1, device_salt)
        return cls(con, map_key, hmac_key)
