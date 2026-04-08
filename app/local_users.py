"""Local user registry with password-based authentication."""

from __future__ import annotations

import hashlib
import os
from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table


def _hash_password(password: str) -> str:
    """Hash a password using scrypt (stdlib, no extra dependencies)."""
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + dk.hex()


def _verify_password(stored_hash: str, password: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
        return dk.hex() == hash_hex
    except Exception:
        return False


class LocalUser(Table):
    """Local user registry -- one row per registered user."""

    class _Meta:
        name = "local_users"
        display_name = "Local Users"
        description = "Local user registry with password-based authentication."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="User ID", db_default="nextval('shenas_system.local_user_seq')"),
    ] = 0
    username: Annotated[str, Field(db_type="VARCHAR", description="Unique display name")] = ""
    password_hash: Annotated[str, Field(db_type="VARCHAR", description="scrypt password hash")] = ""
    remote_token: Annotated[str | None, Field(db_type="VARCHAR", description="shenas.net JWT (optional)")] = None
    created_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When user was created", db_default="current_timestamp"),
    ] = None
    last_login: Annotated[str | None, Field(db_type="TIMESTAMP", description="Last login timestamp")] = None

    @classmethod
    def create(cls, username: str, password: str) -> dict[str, Any]:
        """Create a new local user and return {id, username}."""
        from app.db import cursor

        password_hash = _hash_password(password)
        with cursor() as cur:
            row = cur.execute(
                "INSERT INTO shenas_system.local_users (username, password_hash, created_at) "
                "VALUES (?, ?, now()) RETURNING id, username",
                [username, password_hash],
            ).fetchone()
        if not row:
            msg = "Failed to create user"
            raise RuntimeError(msg)
        return {"id": row[0], "username": row[1]}

    @classmethod
    def authenticate(cls, username: str, password: str) -> dict[str, Any] | None:
        """Verify credentials. Returns {id, username} or None on failure."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username, password_hash FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
        if not row:
            return None
        if not _verify_password(row[2], password):
            return None
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.local_users SET last_login = now() WHERE id = ?",
                [row[0]],
            )
        return {"id": row[0], "username": row[1]}

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        """Return all users as [{id, username}] (no hashes)."""
        from app.db import cursor

        with cursor() as cur:
            rows = cur.execute("SELECT id, username FROM shenas_system.local_users ORDER BY username").fetchall()
        return [{"id": r[0], "username": r[1]} for r in rows]

    @classmethod
    def get_by_id(cls, user_id: int) -> dict[str, Any] | None:
        """Return {id, username} for a user ID, or None if not found."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE id = ?",
                [user_id],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None

    @classmethod
    def set_remote_token(cls, user_id: int, token: str) -> None:
        """Store a shenas.net JWT for an existing local user."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.local_users SET remote_token = ? WHERE id = ?",
                [token, user_id],
            )

    @classmethod
    def find_by_remote_token(cls, token: str) -> dict[str, Any] | None:
        """Find a user by their shenas.net JWT."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE remote_token = ?",
                [token],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None
