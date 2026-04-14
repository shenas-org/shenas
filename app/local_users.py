"""Local user registry with password-based authentication."""

from __future__ import annotations

import contextlib
import hashlib
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field, Table

if TYPE_CHECKING:
    import duckdb

    from app.db import DB


def _hash_password(password: str, salt_hex: str) -> str:
    """Hash a password using scrypt with the given hex salt."""
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return dk.hex()


def _verify_password(stored_hash: str, salt_hex: str, password: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        return _hash_password(password, salt_hex) == stored_hash
    except Exception:
        return False


@dataclass
class LocalUser(Table):
    """Local user registry -- one row per registered user."""

    database: ClassVar[str] = "system"

    # Per-process registry of attached user DBs and the contextvar override.
    _attached: ClassVar[dict[int, Any]] = {}
    _attached_lock: ClassVar[Any] = threading.RLock()

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
    key_salt: Annotated[str, Field(db_type="VARCHAR", description="Salt for deriving DB encryption key")] = ""
    remote_token: Annotated[str | None, Field(db_type="VARCHAR", description="shenas.net JWT (optional)")] = None
    created_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When user was created", db_default="current_timestamp"),
    ] = None
    last_login: Annotated[str | None, Field(db_type="TIMESTAMP", description="Last login timestamp")] = None

    # ------------------------------------------------------------------
    # Per-user DB lifecycle
    # ------------------------------------------------------------------

    @property
    def db_path(self):
        from app.database import DATA_DIR

        return DATA_DIR / "users" / f"{self.id}.duckdb"

    @classmethod
    def _bootstrap_user_db(cls, con: duckdb.DuckDBPyConnection) -> None:  # noqa: PLR0915
        """Create all user-scoped tables in a freshly attached user DB.

        Walks ``Table.__subclasses__()`` recursively, picking every concrete
        subclass that is NOT marked ``database = "system"``. Importing the
        ``app`` package ensures the user-scoped Table subclasses have been
        loaded before discovery runs.
        """

        import app.categories
        import app.data_catalog
        import app.entities
        import app.finding
        import app.hotkeys
        import app.hypotheses
        import app.recipe_cache
        import app.workspace  # noqa: F401

        with contextlib.suppress(ImportError):
            import shenas_datasets.promoted  # noqa: F401

        con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
        con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_instance_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.hypothesis_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.finding_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.entity_seq START 1")

        seen: set[type[Table]] = set()

        def walk(parent: type[Table]) -> None:
            for sub in parent.__subclasses__():
                if sub in seen:
                    continue
                seen.add(sub)
                walk(sub)
                if getattr(sub, "database", "user") == "system":
                    continue
                meta = getattr(sub, "_Meta", None)
                if meta is None or not getattr(meta, "name", None):
                    continue
                schema = getattr(meta, "schema", None) or "main"
                con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                sub.ensure(con, schema=schema)

        walk(Table)

        # Source plugins have Config/Auth SingletonTable subclasses with
        # dynamic names (pipe_<source>) created by Source.__init_subclass__.
        # The MRO walk above misses them because they are generated at
        # class-creation time, not declared as top-level classes. Discover
        # them by walking installed Source subclasses.
        try:
            from shenas_sources.core.source import Source, SourceAuth

            def _ensure_singleton(tbl_cls: Any) -> None:
                meta = getattr(tbl_cls, "_Meta", None)
                if meta is None or not getattr(meta, "name", None):
                    return
                schema = getattr(meta, "schema", None) or "config"
                con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                tbl_cls.ensure(con, schema=schema)

            for source_cls in Source.load_all():
                _ensure_singleton(source_cls.Config)
                if source_cls.Auth is not SourceAuth:
                    _ensure_singleton(source_cls.Auth)
        except Exception:
            pass

        # Dataset plugins define MetricTable subclasses (metrics.daily_sleep,
        # metrics.events, etc.) that transforms write into. Ensure them so
        # the first sync doesn't fail with "table does not exist".
        try:
            from shenas_datasets.core.dataset import Dataset

            Dataset.ensure_all(con)
        except Exception:
            pass

        from app.entities import seed_entity_types, seed_relationship_types
        from app.hotkeys import Hotkey

        Hotkey.seed()
        seed_entity_types(con)
        seed_relationship_types(con)

    def attach(self, key: str) -> DB:
        """Open and attach this user's encrypted DB. Idempotent."""
        from app.db import DB

        cls = type(self)
        with cls._attached_lock:
            db = cls._attached.get(self.id)
            if db is None:
                db = DB(
                    path=self.db_path,
                    key=key,
                    bootstrap=cls._bootstrap_user_db,
                )
                cls._attached[self.id] = db
                db.connect()
                self._ensure_me_entity()
            return db

    @classmethod
    def attach_remembered(cls) -> list[int]:
        """Attach every user whose derived key is stored in the OS keyring.

        Called at server startup so the scheduler can drive syncs for
        users who have opted in to background sync while logged out.
        Returns the list of user_ids that were successfully attached.
        """
        attached: list[int] = []
        for row in cls.list_all():
            user_id = int(row["id"])
            key = cls.get_remembered_key(user_id)
            if not key:
                continue
            user = cls.get_by_id(user_id)
            if user is None:
                continue
            try:
                user.attach(key)
                attached.append(user_id)
            except Exception:
                continue
        return attached

    def detach(self) -> None:
        """Close and forget this user's DB. Idempotent."""
        cls = type(self)
        with cls._attached_lock:
            db = cls._attached.pop(self.id, None)
        if db is not None:
            db.close()

    def _ensure_me_entity(self) -> None:
        """Create the 'me' entity and device entity if they don't exist yet."""
        import platform

        from app.entities import Entity, EntityRelationship

        # Ensure "me" human entity
        me_list = Entity.all(where="type = 'human' AND name = ?", params=[self.username], limit=1)
        me = me_list[0] if me_list else Entity.create(name=self.username, type="human", description="Me")

        # Ensure device entity for this machine
        device_name = platform.node() or "unknown"
        device_list = Entity.all(where="type = 'device' AND name = ?", params=[device_name], limit=1)
        if not device_list:
            device = Entity.create(name=device_name, type="device", description="This device")
            EntityRelationship(from_uuid=me.uuid, to_uuid=device.uuid, type="uses").upsert()

    @classmethod
    def current_db(cls) -> DB:
        """Return the active user's DB based on the ``current_user_id`` contextvar."""
        from app.database import current_user_id

        user_id = current_user_id.get()
        with cls._attached_lock:
            db = cls._attached.get(user_id)
        if db is None:
            msg = f"no user DB attached for user_id={user_id}; call LocalUser.attach() first"
            raise RuntimeError(msg)
        return db

    # ------------------------------------------------------------------
    # CRUD (all on the device-wide registry DB)
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, username: str, password: str) -> LocalUser:
        """Create a new local user and return the row."""
        import os

        salt = os.urandom(16).hex()
        password_hash = _hash_password(password, salt)
        user = cls(username=username, password_hash=password_hash, key_salt=salt)
        user.insert()
        return user

    @classmethod
    def authenticate(cls, username: str, password: str) -> LocalUser | None:
        """Verify credentials. Returns the user row or None on failure."""
        rows = cls.all(where="username = ?", params=[username], limit=1)
        if not rows:
            return None
        user = rows[0]
        if not _verify_password(user.password_hash, user.key_salt, password):
            return None
        return user

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        """Return all users as [{id, username}] (no hashes)."""
        return [{"id": u.id, "username": u.username} for u in cls.all(order_by="username")]

    @classmethod
    def get_by_id(cls, user_id: int) -> LocalUser | None:
        """Return the user row for a user ID, or None if not found."""
        return cls.find(user_id)

    @classmethod
    def get_remote_token(cls) -> str | None:
        """Return the current user's shenas.net token, or None.

        Checks SHENAS_REMOTE_TOKEN env var first (used by tests), then
        falls back to the stored token in local_users.
        """
        import os

        if env := os.environ.get("SHENAS_REMOTE_TOKEN"):
            return env
        try:
            from app.database import current_user_id, cursor

            uid = current_user_id.get()
            if uid is None:
                return None
            with cursor(database="shenas") as cur:
                row = cur.execute(
                    "SELECT remote_token FROM shenas_system.local_users WHERE id = ?",
                    [uid],
                ).fetchone()
            return row[0] if row and row[0] else None
        except Exception:
            return None

    @classmethod
    def set_remote_token(cls, user_id: int, token: str) -> None:
        """Store a shenas.net JWT for a local user (creates row if needed in single-user mode)."""
        user = cls.find(user_id)
        if not user and user_id == 0:
            user = cls(id=0, username="default")
            user.insert()
        if user:
            user.remote_token = token
            user.save()

    @classmethod
    def find_by_remote_token(cls, token: str) -> dict[str, Any] | None:
        """Find a user by their shenas.net JWT."""
        rows = cls.all(where="remote_token = ?", params=[token], limit=1)
        if not rows:
            return None
        return {"id": rows[0].id, "username": rows[0].username}

    # -- Key management --

    @staticmethod
    def derive_key(password: str, salt: str) -> str:
        """Derive a 256-bit DuckDB encryption key from a password + salt via scrypt."""
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return dk.hex()

    @classmethod
    def remember_key(cls, user_id: int, key: str) -> None:
        """Persist a derived user key in the OS keyring."""
        try:
            import keyring

            with contextlib.suppress(Exception):
                keyring.delete_password("shenas", f"user_key_{user_id}")
            keyring.set_password("shenas", f"user_key_{user_id}", key)
        except Exception:
            pass

    @classmethod
    def forget_key(cls, user_id: int) -> None:
        """Remove a remembered user key from the OS keyring."""
        try:
            import keyring

            keyring.delete_password("shenas", f"user_key_{user_id}")
        except Exception:
            pass

    @classmethod
    def get_remembered_key(cls, user_id: int) -> str | None:
        """Return the remembered key for a user, or None if not stored."""
        try:
            import keyring

            return keyring.get_password("shenas", f"user_key_{user_id}")
        except Exception:
            return None
