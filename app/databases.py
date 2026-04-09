"""One generic ``DB`` class plus the resolver wiring.

A ``DB`` is a single in-memory DuckDB parent connection that ATTACHes
one encrypted file under the alias ``db``. Each instance owns its own
connection lifecycle: lazy connect on first use, eager bootstrap of
the tables it should hold, and ``close()`` on logout. There are no
ATTACHing-many-files-into-one-process tricks -- one DB = one file =
one connection.

The shenas server uses two flavors:

- The **device-wide registry**: one ``DB`` instance for the device,
  holding ``LocalUser``, ``LocalSession``, ``SystemSettings``,
  ``PluginInstance``. Accessed via :func:`shenas_db` in ``app.db``.
- The **per-user data**: one ``DB`` instance per logged-in local user,
  with their own password-derived encryption key. Lifecycle (attach
  on login, detach on logout, current-user lookup) is owned by
  :class:`LocalUser` -- which is the natural home for "what does this
  user have?". See ``LocalUser.attach`` / ``LocalUser.detach`` /
  ``LocalUser.current_db``.

The ``Table`` ABC routes its CRUD calls through a small resolver
registry: ``Table.db = "shenas"`` resolves to the registry DB,
``Table.db = None`` (the default) resolves to the current user's DB.
The resolvers themselves are registered from app startup so the
plugin layer stays free of app-level imports.
"""

from __future__ import annotations

import contextlib
import threading
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path


class DB:
    """One logical database = one in-memory parent connection that
    ATTACHes one encrypted file under the alias ``db``.

    Construction is cheap; the underlying connection is opened lazily
    on first :meth:`connect` call. The optional ``bootstrap`` callback
    runs once after the file is attached and the ``USE db`` is set,
    so callers can CREATE TABLE / seed defaults exactly once per
    connection lifetime.
    """

    def __init__(
        self,
        *,
        path: Path,
        key: str,
        bootstrap: Callable[[duckdb.DuckDBPyConnection], None] | None = None,
    ) -> None:
        self.path = path
        self.key = key
        self._bootstrap = bootstrap
        self._con: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.RLock()

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Return the underlying connection, lazily initializing it.

        Detects a stale (closed) connection and re-opens it, which can
        happen when the uvicorn reloader restarts the process while a
        cached DB instance survives in module-level state.
        """
        with self._lock:
            if self._con is not None:
                try:
                    self._con.execute("SELECT 1 FROM db.information_schema.schemata LIMIT 1")
                except Exception:
                    with contextlib.suppress(Exception):
                        self._con.close()
                    self._con = None
            if self._con is None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._con = duckdb.connect()
                self._con.execute(f"ATTACH '{self.path}' AS db (ENCRYPTION_KEY '{self.key}')")
                self._con.execute("USE db")
                if self._bootstrap is not None:
                    self._bootstrap(self._con)
            return self._con

    @contextlib.contextmanager
    def cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Open a child cursor and yield it. Re-pins to ``USE db`` on every
        open in case a previous cursor on the same parent left a stale USE."""
        con = self.connect()
        cur = con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    def close(self) -> None:
        """Close the connection. Idempotent."""
        with self._lock:
            if self._con is not None:
                with contextlib.suppress(Exception):
                    self._con.close()
                self._con = None


# ----------------------------------------------------------------------
# Resolver registry
# ----------------------------------------------------------------------
#
# The plugin layer's ``Table`` ABC needs to route CRUD calls to the
# right DB instance, but it can't import from ``app/`` (layering).
# Instead the app registers a small set of resolvers (one per
# ``Table.db`` tag) at startup and the plugin layer reads from this
# dict. ``Table.db`` is a string tag (``"shenas"``, ``None``, etc.).

_resolvers: dict[str | None, Callable[[], DB]] = {}


def register_db_resolver(tag: str | None, resolver: Callable[[], DB]) -> None:
    """Register a callable that returns the active ``DB`` for a tag.

    Called from app startup. The plugin layer reads this dict in
    :meth:`shenas_plugins.core.table.Table._resolve_db` to find the
    right database for a query.
    """
    _resolvers[tag] = resolver


def resolve_db(tag: str | None) -> DB:
    """Return the active ``DB`` instance for ``tag``."""
    try:
        return _resolvers[tag]()
    except KeyError as exc:
        msg = f"no db resolver registered for tag={tag!r}"
        raise RuntimeError(msg) from exc
