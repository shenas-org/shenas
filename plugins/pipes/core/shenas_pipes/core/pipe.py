"""Pipe plugin ABC."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import logging
import threading
from typing import Any, ClassVar

from shenas_plugins.core.base_auth import PipeAuth
from shenas_plugins.core.base_config import PipeConfig
from shenas_plugins.core.plugin import Plugin
from shenas_plugins.core.store import DataclassStore

logger = logging.getLogger("shenas.pipes")


class Pipe(Plugin):
    """Data pipeline plugin.

    Subclass this, set class attributes, and implement ``resources()``.
    The base class provides default ``sync()`` (build_client -> resources ->
    run_sync -> auto_transform) and auto-derived auth_fields / __table__.
    """

    _kind = "pipe"

    Config: ClassVar[type] = PipeConfig
    Auth: ClassVar[type] = PipeAuth

    auth_instructions: ClassVar[str] = ""
    primary_table: ClassVar[str] = ""

    # Class-level sync lock: prevents concurrent syncs of the same pipe
    _sync_locks: ClassVar[dict[str, threading.Lock]] = {}
    _sync_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    # Populated by __init__
    _config_store: DataclassStore
    _auth_store: DataclassStore

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        # Auto-set __table__ on Config/Auth classes
        if cls.Config is PipeConfig:
            # Pipe uses base PipeConfig -- create a per-pipe subclass so __table__ is unique
            cls.Config = type(f"{cls.name.title()}Config", (PipeConfig,), {"__table__": f"pipe_{cls.name}"})
        elif not hasattr(cls.Config, "__table__"):
            cls.Config.__table__ = f"pipe_{cls.name}"
        if cls.Auth is not PipeAuth and not hasattr(cls.Auth, "__table__"):
            cls.Auth.__table__ = f"pipe_{cls.name}"

    def __init__(self) -> None:
        self._config_store = DataclassStore("config")
        self._auth_store = DataclassStore("auth")

    # -- Auth field derivation ------------------------------------------------

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        """Derive auth input fields from Auth dataclass metadata.

        Override for custom prompts that differ from stored field names.
        """
        if self.Auth is PipeAuth:
            return []
        from shenas_schemas.core.introspect import table_metadata

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
        return self.Auth is not PipeAuth

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
        if self.Config is PipeConfig:
            return None
        try:
            row = self._config_store.get(self.Config)
            return row.get("sync_frequency") if row else None
        except Exception:
            return None

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
        from shenas_schemas.core.introspect import table_metadata

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
            from shenas_schemas.core.introspect import table_metadata

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
            from app.db import update_synced_at

            update_synced_at("pipe", self.name)
        except Exception:
            logger.exception("Failed to update synced_at for %s", self.name)

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Default sync: build_client -> resources -> run_sync -> transform -> mark synced."""
        from shenas_pipes.core.cli import run_sync

        client = self.build_client()
        res = self.resources(client)
        run_sync(self.name, self.name, res, full_refresh, self._auto_transform)
        self._mark_synced()
        self._log_sync_event(full_refresh)

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
        from shenas_pipes.core.db import connect
        from shenas_pipes.core.transform import load_transform_defaults

        defaults = load_transform_defaults(self.name)
        if not defaults:
            return
        from app.transforms import run_transforms, seed_defaults

        con = connect()
        seed_defaults(self.name, defaults)
        count = run_transforms(con, self.name)
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
            from shenas_schemas.core.introspect import table_metadata

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
    from shenas_schemas.core.field import Field

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
