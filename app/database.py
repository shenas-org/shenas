"""Application-level database orchestrator.

Wraps the low-level :class:`app.db.DB` with encryption key management,
the device-wide registry singleton, per-user DB resolution, and
convenience accessors (``cursor``, ``connect``, ``analytics_backend``).

Two flavors of database in shenas:

- The **device-wide registry** -- one DuckDB file holding the local
  user table, sessions, system settings, plugin install state. Lives
  at ``data/shenas.duckdb`` and is accessed via ``shenas_db()``.

- The **per-user data** -- one DuckDB file per local user, encrypted
  with a key derived from the user's password. Created by
  ``LocalUser.attach()`` on login, closed by ``LocalUser.detach()``
  on logout. The "current" user comes from a contextvar set per
  request.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import secrets
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb

from app.db import DB, register_db_resolver

if TYPE_CHECKING:
    from collections.abc import Generator


# Request-scoped user id. Set by middleware, defaults to 0 (single-user).
current_user_id: contextvars.ContextVar[int] = contextvars.ContextVar("current_user_id", default=0)

# Request-scoped entity UUID. None means "the current user's primary entity".
current_entity_uuid: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_entity_uuid", default=None)


class DatabaseManager:
    """Owns the shenas DB singleton, key management, and convenience accessors."""

    def __init__(self) -> None:
        self._shenas_db: DB | None = None
        self._shenas_lock = threading.RLock()
        self.data_dir = self._resolve_data_dir()
        self.shenas_db_path = self.data_dir / "shenas.duckdb"

    # -- Path resolution ---------------------------------------------------

    @staticmethod
    def _resolve_data_dir() -> Path:
        """Resolve the data directory. Uses ~/.shenas/data/ in PyInstaller bundles."""
        import sys

        if getattr(sys, "_MEIPASS", None):
            return Path.home() / ".shenas" / "data"
        return Path("data")

    # -- Key management (static -- no instance state) ----------------------

    @staticmethod
    def get_db_key() -> str:
        """Get the device-wide encryption key from env var or OS keyring."""
        key = os.environ.get("SHENAS_DB_KEY")
        if key:
            return key
        import keyring

        key = keyring.get_password("shenas", "db_key")
        if key:
            return key
        msg = "No database key found. Run 'shenasctl db keygen' or set SHENAS_DB_KEY."
        raise RuntimeError(msg)

    @staticmethod
    def set_db_key(key: str) -> None:
        """Store the device-wide encryption key in the OS keyring."""
        import keyring

        with contextlib.suppress(Exception):
            keyring.delete_password("shenas", "db_key")
        keyring.set_password("shenas", "db_key", key)

    @staticmethod
    def generate_db_key() -> str:
        """Generate a random 256-bit key as a hex string."""
        return secrets.token_hex(32)

    # -- Shenas DB singleton -----------------------------------------------

    def shenas_db(self) -> DB:
        """Return the device-wide registry DB, lazily constructed."""
        with self._shenas_lock:
            if self._shenas_db is None:
                self._shenas_db = DB(
                    path=self.shenas_db_path,
                    key=self.get_db_key(),
                    bootstrap=self._bootstrap_shenas_db,
                )
                self._shenas_db.connect()
            return self._shenas_db

    @staticmethod
    def _bootstrap_shenas_db(con: duckdb.DuckDBPyConnection) -> None:
        """Create the device-wide registry tables."""
        from app.local_sessions import LocalSession
        from app.local_users import LocalUser
        from app.plugin import PluginInstance
        from app.system_settings import SystemSettings

        con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
        for tbl in (LocalUser, LocalSession, SystemSettings, PluginInstance):
            tbl.ensure(con, schema=tbl._Meta.schema or "shenas_system")

        try:
            from app.plugin import VALID_KINDS, Plugin

            for kind in VALID_KINDS:
                try:
                    for cls in Plugin.load_by_kind(kind):
                        if cls.internal:
                            continue
                        row = con.execute(
                            "SELECT 1 FROM shenas_system.plugins WHERE kind = ? AND name = ?",
                            [cls()._kind, cls.name],
                        ).fetchone()
                        if not row:
                            enabled = cls.enabled_by_default or (
                                getattr(cls, "single_active", False) and cls.name == "default"
                            )
                            con.execute(
                                "INSERT INTO shenas_system.plugins (kind, name, enabled) VALUES (?, ?, ?)",
                                [cls()._kind, cls.name, enabled],
                            )
                except Exception:
                    pass
        except Exception:
            pass

    # -- User DB resolver --------------------------------------------------

    def _current_user_db(self) -> DB:
        """Resolver for tables in the current user's DB.

        In single-user mode (current_user_id == 0 with no attached user)
        lazily attaches user_0 backed by the device key.
        """
        from app.local_users import LocalUser

        user_id = current_user_id.get()
        with LocalUser._attached_lock:
            db = LocalUser._attached.get(user_id)
            if db is None and user_id == 0:
                db = DB(
                    path=self.data_dir / "users" / "0.duckdb",
                    key=self.get_db_key(),
                    bootstrap=LocalUser._bootstrap_user_db,
                )
                LocalUser._attached[0] = db
                db.connect()
                # Seed a "me" entity for the default single-user.
                from app.entities import Entity

                if not Entity.all(where="type = 'human'", limit=1):
                    Entity.create(name="me", type="human", description="Default user")
        if db is None:
            msg = f"no user DB attached for user_id={user_id}; call user.attach() first"
            raise RuntimeError(msg)
        return db

    # -- Resolver wiring ---------------------------------------------------

    def register_resolvers(self) -> None:
        """Wire the Table ABC to our DB instances."""
        register_db_resolver("shenas", self.shenas_db)
        register_db_resolver(None, self._current_user_db)

    # -- Convenience accessors ---------------------------------------------

    @contextlib.contextmanager
    def cursor(self, *, database: str | None = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Open a cursor on the named database (default: current user's DB)."""
        from app.db import resolve_db

        db = resolve_db(database)
        with db.cursor() as cur:
            yield cur

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:  # noqa: ARG002
        """Return the current user's underlying DuckDB connection."""
        from app.db import resolve_db

        return resolve_db(None).connect()

    def analytics_backend(self) -> Any:
        """Return an Ibis Backend wrapping a child cursor of the current user's DB."""
        import sys

        import ibis

        cur = sys.modules[__name__].connect().cursor()
        cur.execute("USE db")
        return ibis.duckdb.from_connection(cur)

    # -- dlt helpers -------------------------------------------------------

    @staticmethod
    def dlt_destination() -> tuple[Any, duckdb.DuckDBPyConnection]:
        """Return a dlt DuckDB destination backed by an in-memory connection."""
        import dlt

        mem_con = duckdb.connect(":memory:")
        return dlt.destinations.duckdb(credentials=mem_con), mem_con

    def flush_to_encrypted(self, mem_con: duckdb.DuckDBPyConnection, dataset_name: str) -> None:
        """Copy tables from the in-memory dlt connection into the current user's DB."""
        import sys

        server_con = sys.modules[__name__].connect()

        all_schemas = [r[0] for r in mem_con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
        schemas_to_copy = [s for s in all_schemas if s in (dataset_name, f"{dataset_name}_staging")]

        for schema in schemas_to_copy:
            server_con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            tables = mem_con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = ? AND table_catalog = 'memory'",
                [schema],
            ).fetchall()
            for (table_name,) in tables:
                tmp_name = f"_flush_{schema}_{table_name}".replace("-", "_")
                arrow_tbl = mem_con.execute(f'SELECT * FROM memory."{schema}"."{table_name}"').arrow()
                server_con.register(tmp_name, arrow_tbl)
                server_con.execute(f'CREATE OR REPLACE TABLE "{schema}"."{table_name}" AS SELECT * FROM {tmp_name}')
                server_con.unregister(tmp_name)

        mem_con.close()

    # -- Test support ------------------------------------------------------

    def reset_for_tests(self) -> None:
        """Drop the cached registry DB so tests can re-init against a tmp path."""
        with self._shenas_lock:
            if self._shenas_db is not None:
                self._shenas_db.close()
            self._shenas_db = None

    @staticmethod
    def ensure_system_tables(con: duckdb.DuckDBPyConnection) -> None:
        """Create all system + user tables on a single in-memory connection for tests."""
        from shenas_transformers.core.transform import Transform
        from shenas_transformers.geofence.model import Geofence

        from app.categories import CategorySet, CategoryValue
        from app.data_catalog import QualityCheckResult, ResourceAnnotation
        from app.entities import (
            Entity,
            EntityIndex,
            EntityRelationship,
            EntityRelationshipType,
            EntityType,
            seed_entity_types,
            seed_relationship_types,
        )
        from app.finding import Finding
        from app.hotkeys import Hotkey
        from app.hypotheses import Hypothesis
        from app.local_sessions import LocalSession
        from app.local_users import LocalUser
        from app.plugin import PluginInstance
        from app.recipe_cache import RecipeCache
        from app.system_settings import SystemSettings
        from app.table import Table
        from app.workspace import Workspace
        from shenas_datasets.promoted import PromotedMetric

        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_instance_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.hypothesis_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.finding_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.geofence_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.entity_seq START 1")
        tables: list[type[Table]] = [
            Transform,
            PluginInstance,
            Workspace,
            Hotkey,
            Hypothesis,
            PromotedMetric,
            RecipeCache,
            Finding,
            SystemSettings,
            LocalUser,
            LocalSession,
            Geofence,
            ResourceAnnotation,
            QualityCheckResult,
            CategorySet,
            CategoryValue,
            EntityType,
            EntityRelationshipType,
            Entity,
            EntityIndex,
            EntityRelationship,
        ]
        Table.ensure_schema(con, tables, schema="shenas_system")
        Hotkey.seed()
        seed_entity_types(con)
        seed_relationship_types(con)
        from shenas_datasets.core.dataset import Dataset

        Dataset.ensure_all(con)


# -- Module-level singleton + forwarding aliases ---------------------------

_manager = DatabaseManager()
_manager.register_resolvers()

DATA_DIR = _manager.data_dir
SHENAS_DB_PATH = _manager.shenas_db_path

cursor = _manager.cursor
connect = _manager.connect
shenas_db = _manager.shenas_db
analytics_backend = _manager.analytics_backend
flush_to_encrypted = _manager.flush_to_encrypted

get_db_key = DatabaseManager.get_db_key
set_db_key = DatabaseManager.set_db_key
generate_db_key = DatabaseManager.generate_db_key
dlt_destination = DatabaseManager.dlt_destination

_reset_for_tests = _manager.reset_for_tests
_ensure_system_tables = DatabaseManager.ensure_system_tables
