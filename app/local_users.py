"""Local user registry with password-based authentication."""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, Table


def _hash_password(password: str) -> str:
    """Hash a password using scrypt with a random salt."""
    salt = secrets.token_hex(16)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
    return f"scrypt:{salt}:{h.hex()}"


def _verify_password(stored: str, password: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        _, salt, expected = stored.split(":", 2)
        h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
        return secrets.compare_digest(h.hex(), expected)
    except Exception:
        return False


class LocalUser(Table):
    """Local user registry (one row per user)."""

    table_name: ClassVar[str] = "local_users"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Local Users"
    table_description: ClassVar[str | None] = "Local user registry with password-based authentication."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="User ID")] = 0
    username: Annotated[str, Field(db_type="VARCHAR", description="Display name")] = ""
    password_hash: Annotated[
        str, Field(db_type="VARCHAR", description="Scrypt password hash", category="secret")
    ] = ""
    remote_token: (
        Annotated[str, Field(db_type="VARCHAR", description="shenas.net JWT token", category="secret")] | None
    ) = None
    created_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp")] | None
    ) = None
    last_login: Annotated[str, Field(db_type="TIMESTAMP", description="Last login time")] | None = None

    @classmethod
    def create(cls, username: str, password: str) -> dict:
        """Create a new user. Raises ValueError if username already exists."""
        from app.db import cursor

        cls._ensure_once("shenas_system")
        pw_hash = _hash_password(password)
        with cursor() as cur:
            cur.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
            existing = cur.execute(
                "SELECT id FROM shenas_system.local_users WHERE username = ?", [username]
            ).fetchone()
            if existing:
                msg = f"Username already exists: {username}"
                raise ValueError(msg)
            row = cur.execute(
                "INSERT INTO shenas_system.local_users (id, username, password_hash, created_at)"
                " VALUES (nextval('shenas_system.local_user_seq'), ?, ?, now()) RETURNING id, username",
                [username, pw_hash],
            ).fetchone()
        return {"id": row[0], "username": row[1]}

    @classmethod
    def authenticate(cls, username: str, password: str) -> dict | None:
        """Verify password and return user dict, or None if auth fails."""
        from app.db import cursor

        cls._ensure_once("shenas_system")
        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username, password_hash FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
        if row and _verify_password(row[2], password):
            return {"id": row[0], "username": row[1]}
        return None

    @classmethod
    def list_all(cls) -> list[dict]:
        """Return all users as a list of {id, username} dicts (no hashes)."""
        from app.db import cursor

        cls._ensure_once("shenas_system")
        with cursor() as cur:
            rows = cur.execute(
                "SELECT id, username FROM shenas_system.local_users ORDER BY username"
            ).fetchall()
        return [{"id": r[0], "username": r[1]} for r in rows]

    @classmethod
    def get_by_id(cls, user_id: int) -> dict | None:
        """Return {id, username} for a user by ID, or None."""
        from app.db import cursor

        cls._ensure_once("shenas_system")
        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE id = ?",
                [user_id],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None

    @classmethod
    def find_by_remote_token(cls, token: str) -> dict | None:
        """Return {id, username} for a user linked to a shenas.net token, or None."""
        from app.db import cursor

        cls._ensure_once("shenas_system")
        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE remote_token = ?",
                [token],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None

    @classmethod
    def upsert_remote_user(cls, username: str, remote_token: str) -> dict:
        """Create or find a user linked to a shenas.net OAuth token.

        If a user already has this token, return them.
        If the username exists, update their token.
        Otherwise create a new user with no password (remote-only auth).
        """
        from app.db import cursor

        cls._ensure_once("shenas_system")
        existing = cls.find_by_remote_token(remote_token)
        if existing:
            return existing
        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
            if row:
                cur.execute(
                    "UPDATE shenas_system.local_users SET remote_token = ? WHERE id = ?",
                    [remote_token, row[0]],
                )
                return {"id": row[0], "username": row[1]}
            cur.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
            row = cur.execute(
                "INSERT INTO shenas_system.local_users"
                " (id, username, password_hash, remote_token, created_at)"
                " VALUES (nextval('shenas_system.local_user_seq'), ?, '', ?, now()) RETURNING id, username",
                [username, remote_token],
            ).fetchone()
        return {"id": row[0], "username": row[1]}
