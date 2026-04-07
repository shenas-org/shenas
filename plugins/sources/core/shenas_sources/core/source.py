"""Source plugin ABC."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import logging
import threading
from datetime import UTC
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from shenas_plugins.core.base_auth import SourceAuth
from shenas_plugins.core.base_config import SourceConfig
from shenas_plugins.core.plugin import Plugin
from shenas_plugins.core.store import TableStore

logger = logging.getLogger("shenas.sources")


class Source(Plugin):
    """Data pipeline plugin.

    Subclass this, set class attributes, and implement ``resources()``.
    The base class provides default ``sync()`` (build_client -> resources ->
    run_sync -> auto_transform) and auto-derived auth_fields / table_name.
    """

    _kind = "source"

    Config: ClassVar[type] = SourceConfig
    Auth: ClassVar[type] = SourceAuth

    auth_instructions: ClassVar[str] = ""
    primary_table: ClassVar[str] = ""

    # Class-level sync lock: prevents concurrent syncs of the same pipe
    _sync_locks: ClassVar[dict[str, threading.Lock]] = {}
    _sync_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    # Populated by __init__
    _config_store: TableStore
    _auth_store: TableStore

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        # Auto-set table_name on Config/Auth classes (one row per pipe), then
        # call _finalize() to apply the deferred @dataclass + Table validation.
        if cls.Config is SourceConfig:
            # Source uses base SourceConfig -- create a per-pipe subclass so table_name is unique.
            cls.Config = type(f"{cls.name.title()}Config", (SourceConfig,), {"table_name": f"pipe_{cls.name}"})
        elif not hasattr(cls.Config, "table_name"):
            cls.Config.table_name = f"pipe_{cls.name}"
        cls.Config._finalize()
        if cls.Auth is not SourceAuth:
            if not hasattr(cls.Auth, "table_name"):
                cls.Auth.table_name = f"pipe_{cls.name}"
            cls.Auth._finalize()

    def __init__(self) -> None:
        self._config_store = TableStore("config")
        self._auth_store = TableStore("auth")

    # -- Auth field derivation ------------------------------------------------

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        """Derive auth input fields from Auth dataclass metadata.

        Override for custom prompts that differ from stored field names.
        """
        if self.Auth is SourceAuth:
            return []
        from shenas_plugins.core.introspect import table_metadata

        meta = table_metadata(self.Auth)
        fields: list[dict[str, str | bool]] = []
        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            fields.append(
                {
                    "name": col["name"],
                    "prompt": col.get("description") or col["name"].replace("_", " ").title(),
                    "hide": col.get("category") == "secret",
                }
            )
        return fields

    @property
    def has_auth(self) -> bool:
        return self.Auth is not SourceAuth

    @property
    def is_authenticated(self) -> bool | None:
        """Whether stored credentials exist. None if auth not required."""
        if not self.has_auth:
            return True
        try:
            row = self._auth_store.get(self.Auth)
            return bool(row and any(v for k, v in row.items() if k != "id"))
        except Exception:
            return None

    @property
    def sync_frequency(self) -> int | None:
        """Sync frequency in minutes from config, or None."""
        if self.Config is SourceConfig:
            return None
        try:
            row = self._config_store.get(self.Config)
            return row.get("sync_frequency") if row else None
        except Exception:
            return None

    @property
    def is_due_for_sync(self) -> bool:
        """Whether this source's sync frequency has elapsed since last sync."""
        freq = self.sync_frequency
        if freq is None:
            return False
        s = self.state
        if not s or not s.get("enabled"):
            return False
        synced_at = s.get("synced_at")
        if not synced_at:
            return True
        from datetime import datetime

        last = datetime.fromisoformat(synced_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        from datetime import timedelta

        return datetime.now(UTC) - last >= timedelta(minutes=freq)

    @property
    def has_data(self) -> bool:
        return True  # Pipes sync data into DuckDB

    @property
    def has_config(self) -> bool:
        return True  # All pipes have config (at minimum sync_frequency, lookback_period)

    @property
    def commands(self) -> list[str]:
        cmds = ["sync"]
        if self.has_auth:
            cmds.append("auth")
        return cmds

    def get_config_entries(self) -> list[dict[str, str | None]]:
        """Return config entries for UI display (key, label, value, description)."""
        if not self.has_config:
            return []
        from shenas_plugins.core.introspect import table_metadata

        row = self._config_store.get(self.Config)
        meta = table_metadata(self.Config)
        entries = []
        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            is_secret = col.get("category") == "secret"
            display_val = "********" if (is_secret and val) else (str(val) if val is not None else None)
            entries.append(
                {
                    "key": col["name"],
                    "label": col["name"].replace("_", " ").title(),
                    "value": display_val,
                    "description": col.get("description", ""),
                }
            )
        return entries

    def set_config_value(self, key: str, value: str | None) -> None:
        """Set a config value with type coercion from string."""
        if not self.has_config:
            return
        if value is not None:
            from shenas_plugins.core.introspect import table_metadata

            meta = table_metadata(self.Config)
            for col in meta["columns"]:
                if col["name"] == key:
                    db_type = col.get("db_type", "").upper()
                    if db_type == "INTEGER":
                        value = int(value)  # type: ignore[assignment]
                    elif db_type in ("FLOAT", "DOUBLE", "REAL"):
                        value = float(value)  # type: ignore[assignment]
                    break
        self._config_store.set(self.Config, **{key: value})

    def get_config_value(self, key: str) -> Any | None:
        """Get a single config value."""
        return self._config_store.get_value(self.Config, key) if self.has_config else None

    def delete_config(self) -> None:
        """Delete all config."""
        if self.has_config:
            self._config_store.delete(self.Config)

    def get_info(self) -> dict[str, Any]:
        return {
            **super().get_info(),
            "is_authenticated": self.is_authenticated,
            "sync_frequency": self.sync_frequency,
            "primary_table": self.primary_table,
            "commands": self.commands,
        }

    # -- Sync lifecycle -------------------------------------------------------

    @abc.abstractmethod
    def resources(self, client: Any) -> list[Any]:
        """Return dlt @resource objects for this sync."""
        ...

    def build_client(self) -> Any:
        """Build an API client from stored credentials. Override for auth."""
        return None

    def acquire_sync_lock(self) -> bool:
        """Try to acquire the sync lock for this pipe. Returns False if already locked."""
        with self._sync_locks_guard:
            if self.name not in self._sync_locks:
                self._sync_locks[self.name] = threading.Lock()
        return self._sync_locks[self.name].acquire(blocking=False)

    def release_sync_lock(self) -> None:
        """Release the sync lock for this pipe."""
        with self._sync_locks_guard:
            lock = self._sync_locks.get(self.name)
        if lock is not None:
            with contextlib.suppress(RuntimeError):
                lock.release()

    def _mark_synced(self) -> None:
        """Update the synced_at timestamp in the plugin state table."""
        try:
            self.mark_synced()
        except Exception:
            logger.exception("Failed to update synced_at for %s", self.name)

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Callable[[str, str], None] | None = None,
        **_kwargs: Any,
    ) -> None:
        """Default sync: build_client -> resources -> run_sync -> transform -> mark synced.

        `on_progress`, if given, is forwarded to `run_sync` and called at each
        per-resource checkpoint so streaming consumers can surface progress.
        """
        from shenas_sources.core.as_of import apply_as_of_macros
        from shenas_sources.core.cli import run_sync
        from shenas_sources.core.db import connect

        client = self.build_client()
        res = self.resources(client)
        run_sync(self.name, self.name, res, full_refresh, self._auto_transform, on_progress=on_progress)
        # Refresh AS-OF macros for any SCD2 tables in this source's schema.
        try:
            con = connect()
            try:
                apply_as_of_macros(con, self.name)
            finally:
                con.close()
        except Exception:
            logger.exception("Failed to refresh AS-OF macros for %s", self.name)
        self._mark_synced()
        self._log_sync_event(full_refresh)

    def run_sync_stream(self, *, full_refresh: bool = False) -> Iterator[tuple[str, str]]:
        """Run sync yielding (event, message) tuples for progress reporting.

        Runs the actual sync in a daemon worker thread and drains a queue from
        the generator body so per-resource progress events from `run_sync` flow
        out as they happen instead of all at once when sync completes.
        """
        import queue
        import threading

        from app.jobs import bind_job_id, get_job_id

        logger.info("Sync started: %s", self.name)
        # No "starting sync" yield -- the spinner already shows the job is
        # running, and the next line is always "Fetching (1/N): ...".

        if self.has_auth and not self.is_authenticated:
            msg = "Not authenticated. Configure credentials in the Auth tab."
            logger.warning("Sync skipped: %s -- %s", self.name, msg)
            yield ("error", msg)
            return

        # ContextVars don't propagate across threading.Thread boundaries -- capture
        # the parent's job_id and rebind inside the worker so logs emitted from the
        # sync thread also carry it.
        job_id = get_job_id()
        q: queue.Queue[tuple[str, str] | None] = queue.Queue()

        def _worker() -> None:
            with bind_job_id(job_id):
                try:
                    self.sync(full_refresh=full_refresh, on_progress=lambda e, m: q.put((e, m)))
                    label = getattr(self, "display_name", None) or self.name
                    q.put(("__done__", f"Sync complete: {label}"))
                except Exception as exc:
                    logger.exception("Sync failed: %s", self.name)
                    q.put(("__error__", str(exc)))
                finally:
                    q.put(None)  # sentinel: end-of-stream

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        while True:
            try:
                item = q.get(timeout=0.5)
            except queue.Empty:
                if not t.is_alive():
                    break
                continue
            if item is None:  # sentinel
                break
            evt, msg = item
            if evt == "__done__":
                logger.info("Sync complete: %s", self.name)
                yield ("complete", msg)
            elif evt == "__error__":
                yield ("error", msg)
                return
            else:
                # fetch_start / fetch_done / flush / transform_start -- all "progress"
                yield ("progress", msg)
        # Daemon thread exits with the process; nothing to join. We can't cancel
        # an in-flight dlt run cleanly anyway.

    def _log_sync_event(self, full_refresh: bool) -> None:
        """Append a sync event to the mesh sync log."""
        try:
            from app.mesh.sync_log import append_event

            append_event(
                table_schema=self.name,
                table_name="*",
                operation="full_refresh" if full_refresh else "sync",
            )
        except Exception:
            pass  # mesh not initialized yet

    def _auto_transform(self) -> None:
        """Run transforms if this pipe has a transforms.json."""
        from shenas_sources.core.db import connect
        from shenas_sources.core.transform import load_transform_defaults

        defaults = load_transform_defaults(self.name)
        if not defaults:
            return
        from app.transforms import Transform

        con = connect()
        Transform.seed_defaults(self.name, defaults)
        count = Transform.run_for_source(con, self.name)
        logger.info("Transforms done: %s (%d)", self.name, count)

    # -- Auth flow ------------------------------------------------------------

    def authenticate(self, credentials: dict[str, str]) -> None:
        """Handle credential submission. Override for auth."""

    def complete_mfa(self, state: dict[str, Any], mfa_code: str) -> None:
        """Complete a multi-step MFA flow. Override if needed."""
        msg = f"{self.name} does not support MFA"
        raise NotImplementedError(msg)

    def get_pending_mfa_state(self) -> dict[str, Any] | None:
        """Return pending MFA state, or None. Override if pipe supports MFA."""
        return None

    @property
    def stored_credentials(self) -> list[str]:
        """Labels for stored credential fields that have values."""
        if not self.has_auth:
            return []
        try:
            from shenas_plugins.core.introspect import table_metadata

            row = self._auth_store.get(self.Auth)
            meta = table_metadata(self.Auth)
            return [
                col["name"].replace("_", " ").title()
                for col in meta["columns"]
                if col["name"] != "id" and row and row.get(col["name"])
            ]
        except Exception:
            return []

    def handle_auth(self, credentials: dict[str, str]) -> dict[str, Any]:  # noqa: PLR0911
        """Dispatch auth flow. Returns a result dict for the API response.

        Result keys: ok, message, error, needs_mfa, oauth_url.
        """
        # MFA completion
        if "mfa_code" in credentials:
            state = self.get_pending_mfa_state()
            if state is None:
                return {"ok": False, "error": "No pending MFA session. Start auth again."}
            try:
                self.complete_mfa(state, credentials["mfa_code"])
                return {"ok": True, "message": f"Authenticated {self.name}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # OAuth completion
        if "auth_complete" in credentials:
            try:
                self.authenticate(credentials)
                return {"ok": True, "message": f"Authenticated {self.name}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # Initial auth
        try:
            self.authenticate(credentials)
            return {"ok": True, "message": f"Authenticated {self.name}"}
        except ValueError as exc:
            msg = str(exc)
            if "MFA code required" in msg:
                return {"ok": False, "needs_mfa": True, "message": "MFA code required"}
            if msg.startswith("OAUTH_URL:"):
                return {
                    "ok": False,
                    "oauth_url": msg.removeprefix("OAUTH_URL:"),
                    "message": "Open this URL in your browser to authorize",
                }
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_field_meta(f: dataclasses.Field) -> dict[str, Any]:  # type: ignore[type-arg]
    """Extract Field metadata from an Annotated dataclass field."""
    from shenas_plugins.core.field import Field

    hints = getattr(f.type, "__metadata__", ()) if hasattr(f.type, "__metadata__") else ()
    # Unwrap Optional[Annotated[...]]
    if not hints and hasattr(f.type, "__args__"):
        for arg in f.type.__args__:
            if hasattr(arg, "__metadata__"):
                hints = arg.__metadata__
                break
    for h in hints:
        if isinstance(h, Field):
            return dataclasses.asdict(h)
    return {}
