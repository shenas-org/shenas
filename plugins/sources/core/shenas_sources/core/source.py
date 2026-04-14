"""Source plugin ABC."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import logging
import re
import threading
from datetime import UTC
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from app.plugin import Plugin
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig

logger = logging.getLogger("shenas.sources")

# ISO 8601 recurring-interval parser: "R/P1D", "R/PT1H", "R/P2W", "R/PT15M", etc.
# Supports the subset of durations we actually use for sync cadence: weeks,
# days, hours, minutes, seconds. Returns minutes (or None on parse failure /
# empty input). Kept inline to avoid pulling in `isodate`.
_ISO_RECURRING_RE = re.compile(
    r"^R/P(?:(?P<weeks>\d+)W)?"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def _iso8601_recurring_to_minutes(value: str) -> int | None:
    """Parse an ISO 8601 recurring interval like ``R/P1D`` to minutes.

    Returns ``None`` if ``value`` is empty or not a recognized pattern.
    """
    if not value:
        return None
    m = _ISO_RECURRING_RE.match(value)
    if not m:
        return None
    parts = {k: int(v) for k, v in m.groupdict().items() if v}
    if not parts:
        return None
    total = (
        parts.get("weeks", 0) * 7 * 24 * 60
        + parts.get("days", 0) * 24 * 60
        + parts.get("hours", 0) * 60
        + parts.get("minutes", 0)
        + parts.get("seconds", 0) // 60
    )
    return total or None


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
    entity_types: ClassVar[list[str]] = ["human"]  # references EntityType.name
    # ISO 8601 recurring interval describing the source's natural cadence
    # (e.g. "R/P1D" for daily, "R/P1W" for weekly, "R/PT1H" for hourly).
    # Mirrors DCAT's `dct:accrualPeriodicity`. Used as the fallback when
    # the per-instance `sync_frequency` config row is unset (see
    # :meth:`sync_frequency`). Empty string means no default cadence.
    default_update_frequency: ClassVar[str] = ""

    # Class-level sync lock: prevents concurrent syncs of the same pipe
    _sync_locks: ClassVar[dict[str, threading.Lock]] = {}
    _sync_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        # Auto-set _Meta.name on Config/Auth classes (one row per pipe), then
        # call _finalize() to apply the deferred @dataclass + Table validation.
        per_pipe_name = f"pipe_{cls.name}"
        if cls.Config is SourceConfig:
            # Source uses base SourceConfig -- create a per-pipe subclass so the table name is unique.
            per_pipe_meta = type("_Meta", (SourceConfig._Meta,), {"name": per_pipe_name})
            cls.Config = type(f"{cls.name.title()}Config", (SourceConfig,), {"_Meta": per_pipe_meta})
        elif getattr(cls.Config._Meta, "name", None) in (None, ""):  # ty: ignore[unresolved-attribute]
            cls.Config._Meta = type("_Meta", (cls.Config._Meta,), {"name": per_pipe_name})  # ty: ignore[invalid-assignment, unresolved-attribute]
        cls.Config._finalize()  # ty: ignore[unresolved-attribute]
        if cls.Auth is not SourceAuth:
            if getattr(cls.Auth._Meta, "name", None) in (None, ""):  # ty: ignore[unresolved-attribute]
                cls.Auth._Meta = type("_Meta", (cls.Auth._Meta,), {"name": per_pipe_name})  # ty: ignore[invalid-assignment, unresolved-attribute]
            cls.Auth._finalize()  # ty: ignore[unresolved-attribute]
        # Auto-set _Meta.schema on every SourceTable in this source's TABLES
        # tuple so the catalog can qualify references like `strava.activities`.
        # Discovery is by convention: each source's tables module is at
        # ``shenas_sources.<source_name>.tables`` and exports a ``TABLES``
        # tuple. The lazy import here mirrors the lazy import in
        # ``Source.resources()`` and stays tolerant of plugins that don't
        # follow the convention (or have no source-side raw tables at all).
        try:
            import importlib

            tables_mod = importlib.import_module(f"shenas_sources.{cls.name}.tables")
            for t in getattr(tables_mod, "TABLES", ()):
                if not getattr(t._Meta, "schema", None):
                    t._Meta = type("_Meta", (t._Meta,), {"schema": cls.name})
        except ImportError:
            pass

    # -- Auth field derivation ------------------------------------------------

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        """Derive auth input fields from Auth dataclass metadata.

        Override for custom prompts that differ from stored field names.
        """
        if self.Auth is SourceAuth:
            return []

        columns = self.Auth.column_metadata()  # ty: ignore[unresolved-attribute]
        fields: list[dict[str, str | bool]] = []
        for col in columns:
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
            row = self.Auth.read_row()  # ty: ignore[unresolved-attribute]
            return bool(row and any(v for k, v in row.items() if k != "id"))
        except Exception:
            return None

    @property
    def sync_frequency(self) -> int | None:
        """Sync frequency in minutes.

        Order of precedence:

        1. Explicit ``sync_frequency`` on the per-instance Config row.
        2. ``default_update_frequency`` ClassVar parsed from ISO 8601
           (e.g. ``"R/P1D"`` -> 1440 minutes).
        3. ``None`` (no scheduled sync).
        """
        if self.Config is not SourceConfig:
            try:
                row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
                if row and row.get("sync_frequency") is not None:
                    return row["sync_frequency"]
            except Exception:
                pass
        return _iso8601_recurring_to_minutes(self.default_update_frequency)

    @property
    def is_due_for_sync(self) -> bool:
        """Whether this source's sync frequency has elapsed since last sync."""
        freq = self.sync_frequency
        if freq is None:
            return False
        s = self.instance()
        if not s or not s.enabled:
            return False
        synced_at = s.synced_at
        if not synced_at:
            return True
        from datetime import datetime, timedelta

        # DuckDB TIMESTAMP columns come back as ``datetime``; legacy rows may
        # still hold an ISO string. Accept both.
        if isinstance(synced_at, datetime):
            last = synced_at
        else:
            try:
                last = datetime.fromisoformat(str(synced_at))
            except (TypeError, ValueError):
                return True
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
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

        row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
        columns = self.Config.column_metadata()  # ty: ignore[unresolved-attribute]
        entries = []
        for col in columns:
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
            columns = self.Config.column_metadata()  # ty: ignore[unresolved-attribute]
            for col in columns:
                if col["name"] == key:
                    db_type = col.get("db_type", "").upper()
                    if db_type == "INTEGER":
                        value = int(value)  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
                    elif db_type in ("FLOAT", "DOUBLE", "REAL"):
                        value = float(value)  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
                    break
        self.Config.write_row(**{key: value})  # ty: ignore[unresolved-attribute]

    def get_config_value(self, key: str) -> Any | None:
        """Get a single config value."""
        return self.Config.read_value(key) if self.has_config else None  # ty: ignore[unresolved-attribute]

    def delete_config(self) -> None:
        """Delete all config."""
        if self.has_config:
            self.Config.clear_rows()  # ty: ignore[unresolved-attribute]

    def get_info(self) -> dict[str, Any]:
        return {
            **super().get_info(),
            "is_authenticated": self.is_authenticated,
            "sync_frequency": self.sync_frequency,
            "primary_table": self.primary_table,
            "entity_types": self.entity_types,
            "default_update_frequency": self.default_update_frequency,
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

    @property
    def dataset_name(self) -> str:
        """DuckDB schema name for this source's raw data.

        When ``current_entity_uuid`` is set to a non-primary entity, the
        schema is suffixed with ``__e<uuid8>`` so each entity's raw data
        lives in its own namespace.
        """
        from app.database import current_entity_uuid, current_user_id
        from app.local_users import LocalUser

        entity_uuid = current_entity_uuid.get()
        if entity_uuid is None:
            return self.name
        # Check if this is the primary (current user's) entity
        user_id = current_user_id.get()
        user = LocalUser.get_by_id(user_id) if user_id else None
        if user and getattr(user, "uuid", None) == entity_uuid:
            return self.name
        return f"{self.name}__e{entity_uuid[:8]}"

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
        """Update the synced_at timestamp in the plugin state table and data catalog."""
        try:
            self.get_or_create_instance().mark_synced()
        except Exception:
            logger.exception("Failed to update synced_at for %s", self.name)
        try:
            from app.data_catalog import catalog

            catalog().mark_refreshed(self.name)
        except Exception:
            pass

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
        run_sync(self.name, self.dataset_name, res, full_refresh, self._auto_transform, on_progress=on_progress)
        # Refresh AS-OF macros for any SCD2 tables in this source's schema.
        try:
            con = connect()
            try:
                apply_as_of_macros(con, self.dataset_name)
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

        # Pre-check: try building the client to catch config errors early
        # without a full traceback in the logs.
        try:
            self.build_client()
        except Exception as exc:
            msg = str(exc)
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
        """Seed and run transforms via the Transform plugin system."""
        from shenas_transformers.core import Transformer
        from shenas_transformers.core.transform import Transform

        from shenas_sources.core.db import connect

        con = connect()

        for cls in Transformer.load_all():
            plugin = cls()
            inst = plugin.instance()
            if not inst or inst.enabled:
                plugin.seed_defaults_for_source(self.name)

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
            row = self.Auth.read_row()  # ty: ignore[unresolved-attribute]
            columns = self.Auth.column_metadata()  # ty: ignore[unresolved-attribute]
            return [
                col["name"].replace("_", " ").title()
                for col in columns
                if col["name"] != "id" and row and row.get(col["name"])
            ]
        except Exception:
            return []

    # -- OAuth redirect flow (new) --

    @property
    def supports_oauth_redirect(self) -> bool:
        """True if this source supports the server-side OAuth redirect flow."""
        return False

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:
        """Generate an OAuth authorization URL. Override for OAuth sources.

        ``credentials`` may contain user-provided values (client_id, etc.)
        collected from auth_fields before the redirect.
        ``redirect_uri`` is the server callback URL the provider should return to.
        Returns the full authorization URL to redirect the browser to.
        """
        msg = f"{self.name} does not support OAuth redirect flow"
        raise NotImplementedError(msg)

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:
        """Exchange an auth code for tokens and store them. Override for OAuth sources."""
        msg = f"{self.name} does not support OAuth redirect flow"
        raise NotImplementedError(msg)

    def handle_auth(self, credentials: dict[str, str], *, redirect_uri: str | None = None) -> dict[str, Any]:  # noqa: PLR0911
        """Dispatch auth flow. Returns a result dict for the API response.

        Result keys: ok, message, error, needs_mfa, oauth_url, oauth_redirect.
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

        # OAuth redirect flow (new)
        if self.supports_oauth_redirect and redirect_uri:
            try:
                url = self.start_oauth(redirect_uri, credentials or None)
                return {"ok": False, "oauth_redirect": url, "message": "Redirecting to authorize..."}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # Legacy OAuth completion (auth_complete flag)
        if "auth_complete" in credentials:
            try:
                self.authenticate(credentials)
                return {"ok": True, "message": f"Authenticated {self.name}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # Initial auth (API key, email/password, or legacy OAuth)
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
    from app.table import Field

    hints = getattr(f.type, "__metadata__", ()) if hasattr(f.type, "__metadata__") else ()
    # Unwrap Optional[Annotated[...]]
    if not hints and hasattr(f.type, "__args__"):
        for arg in f.type.__args__:  # ty: ignore[not-iterable]
            if hasattr(arg, "__metadata__"):
                hints = arg.__metadata__
                break
    for h in hints:
        if isinstance(h, Field):
            return dataclasses.asdict(h)
    return {}
