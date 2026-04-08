"""Local user registry with scrypt password-based authentication."""

from __future__ import annotations

import hashlib
import os
from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, Table


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + dk.hex()


def _verify_password(stored_hash: str, password: str) -> bool:
    try:
        salt_hex, dk_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return dk.hex() == dk_hex
    except Exception:
        return False


class LocalUser(Table):
    table_name: ClassVar[str] = "local_users"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Local Users"
    table_description: ClassVar[str | None] = "Local user registry with password-based authentication."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="User ID",
            db_default="nextval('shenas_system.local_user_seq')",
        ),
    ] = 0
    username: Annotated[str, Field(db_type="VARCHAR", description="Unique username")] = ""
    password_hash: Annotated[str, Field(db_type="VARCHAR", description="Scrypt password hash")] = ""
    remote_token: (
        Annotated[str, Field(db_type="VARCHAR", description="shenas.net JWT token")] | None
    ) = None
    created_at: (
        Annotated[
            str,
            Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp"),
        ]
        | None
    ) = None
    last_login: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When last logged in")] | None
    ) = None

    @classmethod
    def create(cls, username: str, password: str) -> dict:
        from app.db import cursor

        password_hash = _hash_password(password)
        with cursor() as cur:
            row = cur.execute(
                "INSERT INTO shenas_system.local_users (username, password_hash)"
                " VALUES (?, ?) RETURNING id, username",
                [username, password_hash],
            ).fetchone()
        if not row:
            msg = "Failed to create user"
            raise RuntimeError(msg)
        return {"id": row[0], "username": row[1]}

    @classmethod
    def authenticate(cls, username: str, password: str) -> dict | None:
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username, password_hash FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
        if not row or not _verify_password(row[2], password):
            return None
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.local_users SET last_login = current_timestamp WHERE id = ?",
                [row[0]],
            )
        return {"id": row[0], "username": row[1]}

    @classmethod
    def list_all(cls) -> list[dict]:
        from app.db import cursor

        with cursor() as cur:
            rows = cur.execute(
                "SELECT id, username FROM shenas_system.local_users ORDER BY username"
            ).fetchall()
        return [{"id": r[0], "username": r[1]} for r in rows]

    @classmethod
    def get_by_id(cls, user_id: int) -> dict | None:
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE id = ?",
                [user_id],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None

    @classmethod
    def upsert_remote_user(cls, username: str, remote_token: str) -> dict:
        """Look up or create a local user linked to a shenas.net account."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
        if row:
            with cursor() as cur:
                cur.execute(
                    "UPDATE shenas_system.local_users SET remote_token = ? WHERE id = ?",
                    [remote_token, row[0]],
                )
            return {"id": row[0], "username": row[1]}
        # Create a remote-only user (no local password)
        with cursor() as cur:
            new_row = cur.execute(
                "INSERT INTO shenas_system.local_users (username, password_hash, remote_token)"
                " VALUES (?, '', ?) RETURNING id, username",
                [username, remote_token],
            ).fetchone()
        if not new_row:
            msg = "Failed to create remote user"
            raise RuntimeError(msg)
        return {"id": new_row[0], "username": new_row[1]}
