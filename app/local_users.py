"""Local user registry with password-based authentication."""

from __future__ import annotations

import contextlib
import hashlib
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    import duckdb

    from app.databases import DB


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
        from app.db import DATA_DIR

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
        import app.hotkeys
        import app.hypotheses
        import app.literature
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
            from app.api.sources import _load_plugins
            from shenas_sources.core.source import Source, SourceAuth

            def _ensure_singleton(tbl_cls: Any) -> None:
                meta = getattr(tbl_cls, "_Meta", None)
                if meta is None or not getattr(meta, "name", None):
                    return
                schema = getattr(meta, "schema", None) or "config"
                con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                tbl_cls.ensure(con, schema=schema)

            for source_cls in _load_plugins("source", base=Source):
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

        from app.hotkeys import Hotkey

        Hotkey.seed(con)

    def attach(self, key: str) -> DB:
        """Open and attach this user's encrypted DB. Idempotent."""
        from app.databases import DB

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
            return db

    @classmethod
    def attach_remembered(cls) -> list[int]:
        """Attach every user whose derived key is stored in the OS keyring.

        Called at server startup so the scheduler can drive syncs for
        users who have opted in to background sync while logged out.
        Returns the list of user_ids that were successfully attached.
        """
        from app.user_keys import get_remembered_user_key

        attached: list[int] = []
        for row in cls.list_all():
            user_id = int(row["id"])
            key = get_remembered_user_key(user_id)
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

    @classmethod
    def current_db(cls) -> DB:
        """Return the active user's DB based on the ``current_user_id`` contextvar."""
        from app.db import current_user_id

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
        from app.db import cursor
        from app.user_keys import gen_salt

        salt = gen_salt()
        password_hash = _hash_password(password, salt)
        with cursor(database="shenas") as cur:
            row = cur.execute(
                "INSERT INTO shenas_system.local_users (username, password_hash, key_salt, created_at) "
                "VALUES (?, ?, ?, now()) RETURNING id, username, key_salt",
                [username, password_hash, salt],
            ).fetchone()
        if not row:
            msg = "Failed to create user"
            raise RuntimeError(msg)
        return cls(id=row[0], username=row[1], password_hash=password_hash, key_salt=row[2])

    @classmethod
    def authenticate(cls, username: str, password: str) -> LocalUser | None:
        """Verify credentials. Returns the user row or None on failure."""
        from app.db import cursor

        with cursor(database="shenas") as cur:
            row = cur.execute(
                "SELECT id, username, password_hash, key_salt FROM shenas_system.local_users WHERE username = ?",
                [username],
            ).fetchone()
        if not row:
            return None
        if not _verify_password(row[2], row[3], password):
            return None
        with cursor(database="shenas") as cur:
            cur.execute(
                "UPDATE shenas_system.local_users SET last_login = now() WHERE id = ?",
                [row[0]],
            )
        return cls(id=row[0], username=row[1], password_hash=row[2], key_salt=row[3])

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        """Return all users as [{id, username}] (no hashes)."""
        from app.db import cursor

        with cursor(database="shenas") as cur:
            rows = cur.execute("SELECT id, username FROM shenas_system.local_users ORDER BY username").fetchall()
        return [{"id": r[0], "username": r[1]} for r in rows]

    @classmethod
    def get_by_id(cls, user_id: int) -> LocalUser | None:
        """Return the user row for a user ID, or None if not found."""
        from app.db import cursor

        with cursor(database="shenas") as cur:
            row = cur.execute(
                "SELECT id, username, password_hash, key_salt FROM shenas_system.local_users WHERE id = ?",
                [user_id],
            ).fetchone()
        return cls(id=row[0], username=row[1], password_hash=row[2], key_salt=row[3]) if row else None

    @classmethod
    def set_remote_token(cls, user_id: int, token: str) -> None:
        """Store a shenas.net JWT for an existing local user."""
        from app.db import cursor

        with cursor(database="shenas") as cur:
            cur.execute(
                "UPDATE shenas_system.local_users SET remote_token = ? WHERE id = ?",
                [token, user_id],
            )

    @classmethod
    def find_by_remote_token(cls, token: str) -> dict[str, Any] | None:
        """Find a user by their shenas.net JWT."""
        from app.db import cursor

        with cursor(database="shenas") as cur:
            row = cur.execute(
                "SELECT id, username FROM shenas_system.local_users WHERE remote_token = ?",
                [token],
            ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None
