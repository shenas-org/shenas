"""Centralized DuckDB connection state.

Two flavors of database in shenas:

- The **device-wide registry** -- one DuckDB file holding the local
  user table, sessions, system settings, plugin install state. Lives
  at ``data/shenas.duckdb`` and is accessed via :func:`shenas_db`.

- The **per-user data** -- one DuckDB file per local user, encrypted
  with a key derived from the user's password. Created by
  ``LocalUser.attach()`` on login, closed by ``LocalUser.detach()``
  on logout. The "current" user comes from a contextvar set per
  request.

Both flavors are wrapped in the generic :class:`app.databases.DB`
class. The ``Table`` ABC routes CRUD calls through registered
resolvers (see :mod:`app.databases`); ``Table.db = "shenas"`` goes to
the registry, ``Table.db is None`` (the default) goes to the current
user's DB.
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

from app.databases import DB, register_db_resolver

if TYPE_CHECKING:
    from collections.abc import Generator


# ----------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------


def _resolve_data_dir() -> Path:
    """Resolve the data directory. Uses ~/.shenas/data/ in PyInstaller bundles."""
    import sys

    if getattr(sys, "_MEIPASS", None):
        return Path.home() / ".shenas" / "data"
    return Path("data")


DATA_DIR = _resolve_data_dir()
SHENAS_DB_PATH = DATA_DIR / "shenas.duckdb"


# ----------------------------------------------------------------------
# Current user contextvar
# ----------------------------------------------------------------------

# Set per-request by the GraphQL context-getter (and any middleware
# that knows the user). Defaults to 0 = single-user mode. Read by the
# Table ABC's resolver indirectly via :func:`LocalUser.current_db`.
current_user_id: contextvars.ContextVar[int] = contextvars.ContextVar("current_user_id", default=0)


# ----------------------------------------------------------------------
# Encryption key (device-wide for the registry; per-user for users)
# ----------------------------------------------------------------------


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


def set_db_key(key: str) -> None:
    """Store the device-wide encryption key in the OS keyring."""
    import keyring

    with contextlib.suppress(Exception):
        keyring.delete_password("shenas", "db_key")
    keyring.set_password("shenas", "db_key", key)


def generate_db_key() -> str:
    """Generate a random 256-bit key as a hex string."""
    return secrets.token_hex(32)


# ----------------------------------------------------------------------
# The shenas (registry) DB singleton
# ----------------------------------------------------------------------

_shenas_db: DB | None = None
_shenas_lock = threading.RLock()


def _bootstrap_shenas_db(con: duckdb.DuckDBPyConnection) -> None:
    """Create the device-wide registry tables."""
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser
    from app.system_settings import SystemSettings
    from shenas_plugins.core.plugin import PluginInstance

    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
    for tbl in (LocalUser, LocalSession, SystemSettings, PluginInstance):
        tbl.ensure(con, schema=tbl._Meta.schema or "shenas_system")


def shenas_db() -> DB:
    """Return the device-wide registry DB, lazily constructed."""
    global _shenas_db
    with _shenas_lock:
        if _shenas_db is None:
            _shenas_db = DB(
                path=SHENAS_DB_PATH,
                key=get_db_key(),
                bootstrap=_bootstrap_shenas_db,
            )
            _shenas_db.connect()
        return _shenas_db


# ----------------------------------------------------------------------
# Resolver registration
# ----------------------------------------------------------------------
#
# Wires the Table ABC to our DB instances. ``Table.db = "shenas"``
# tables (LocalUser, etc.) route to ``shenas_db()``. The default
# (``Table.db is None``) routes to the current user's DB via
# ``LocalUser.current_db()``.


def _current_user_db() -> DB:
    """Resolver for tables that live in the current user's DB.

    In single-user mode (current_user_id == 0 with no attached user)
    we lazily attach the default user_0 backed by the device key. This
    keeps the existing single-user codepaths working without forcing a
    login flow.
    """
    from app.databases import DB
    from app.local_users import LocalUser

    user_id = current_user_id.get()
    with LocalUser._attached_lock:
        db = LocalUser._attached.get(user_id)
        if db is None and user_id == 0:
            db = DB(
                path=DATA_DIR / "users" / "0.duckdb",
                key=get_db_key(),
                bootstrap=LocalUser._bootstrap_user_db,
            )
            db.connect()
            LocalUser._attached[0] = db
    if db is None:
        msg = f"no user DB attached for user_id={user_id}; call user.attach() first"
        raise RuntimeError(msg)
    return db


register_db_resolver("shenas", shenas_db)
register_db_resolver(None, _current_user_db)


# ----------------------------------------------------------------------
# Test hook
# ----------------------------------------------------------------------


def _reset_for_tests() -> None:
    """Drop the cached registry DB so tests can re-init against a tmp path."""
    global _shenas_db
    with _shenas_lock:
        if _shenas_db is not None:
            _shenas_db.close()
        _shenas_db = None


# ----------------------------------------------------------------------
# Convenience: cursor() and connect() shims
# ----------------------------------------------------------------------
#
# Existing call sites import ``cursor`` from ``app.db``. Today the
# default routes to the current user's DB; pass ``database="shenas"``
# (or future tags) to route elsewhere. The ``connect()`` shim exists
# only for back-compat with legacy code that wants the underlying
# DuckDB connection -- new code should use ``shenas_db()`` /
# ``LocalUser.current_db()`` directly.


@contextlib.contextmanager
def cursor(*, database: str | None = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Open a cursor on the named database (default: current user's DB).

    ``database="shenas"`` -> the registry DB.
    ``database=None`` (default) -> the current user's DB.
    """
    from app.databases import resolve_db

    db = resolve_db(database)
    with db.cursor() as cur:
        yield cur


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:  # noqa: ARG001
    """Back-compat shim: return the current user's underlying connection."""
    from app.databases import resolve_db

    return resolve_db(None).connect()


# ----------------------------------------------------------------------
# Analytics backend (Ibis) -- runs against the current user's DB
# ----------------------------------------------------------------------


def analytics_backend() -> Any:
    """Return an Ibis Backend wrapping a child cursor of the current user's DB."""
    import ibis

    cur = connect().cursor()
    cur.execute("USE db")
    return ibis.duckdb.from_connection(cur)


# ----------------------------------------------------------------------
# dlt destination + flush
# ----------------------------------------------------------------------


def dlt_destination() -> tuple[Any, duckdb.DuckDBPyConnection]:
    """Return a dlt DuckDB destination backed by an in-memory connection."""
    import dlt

    mem_con = duckdb.connect(":memory:")
    return dlt.destinations.duckdb(credentials=mem_con), mem_con


def flush_to_encrypted(mem_con: duckdb.DuckDBPyConnection, dataset_name: str) -> None:
    """Copy tables from the in-memory dlt connection into the current user's DB."""
    server_con = connect()

    all_schemas = [r[0] for r in mem_con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
    schemas_to_copy = [s for s in all_schemas if s in (dataset_name, f"{dataset_name}_staging")]

    for schema in schemas_to_copy:
        server_con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        tables = mem_con.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}' AND table_catalog = 'memory'"
        ).fetchall()
        for (table_name,) in tables:
            tmp_name = f"_flush_{schema}_{table_name}".replace("-", "_")
            arrow_tbl = mem_con.execute(f'SELECT * FROM memory."{schema}"."{table_name}"').arrow()
            server_con.register(tmp_name, arrow_tbl)
            server_con.execute(f'CREATE OR REPLACE TABLE "{schema}"."{table_name}" AS SELECT * FROM {tmp_name}')
            server_con.unregister(tmp_name)

    mem_con.close()


# ----------------------------------------------------------------------
# Test back-compat shim
# ----------------------------------------------------------------------


def _ensure_system_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Back-compat shim for test fixtures that pass a single in-memory connection.

    Older test fixtures construct ``con = duckdb.connect(":memory:")``,
    ATTACH ``:memory:`` AS db, USE db, and call this. The new design
    splits state across two DBs, but tests that exercise either side
    can run both bootstraps against the same connection so the legacy
    fixture pattern keeps working.
    """
    from app.hotkeys import Hotkey
    from app.hypotheses import Hypothesis
    from app.local_sessions import LocalSession
    from app.local_users import LocalUser
    from app.recipe_cache import RecipeCache
    from app.system_settings import SystemSettings
    from app.transforms import Transform
    from app.workspace import Workspace
    from shenas_datasets.promoted import PromotedMetric
    from shenas_plugins.core.plugin import PluginInstance
    from shenas_plugins.core.table import Table

    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_seq START 1")
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.hypothesis_seq START 1")
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.local_user_seq START 1")
    tables: list[type[Table]] = [
        Transform,
        PluginInstance,
        Workspace,
        Hotkey,
        Hypothesis,
        PromotedMetric,
        RecipeCache,
        SystemSettings,
        LocalUser,
        LocalSession,
    ]
    Table.ensure_schema(con, tables, schema="shenas_system")
    Hotkey.seed(con)
    from shenas_datasets.core.dataset import Dataset

    Dataset.ensure_all(con)


# Compatibility re-export for legacy callers.
DB_PATH = SHENAS_DB_PATH
