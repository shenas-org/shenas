"""Abstract base classes for all shenas plugin kinds.

Plugin
  |-- Pipe          (data pipeline with sync, auth, config)
  |-- Schema        (canonical metrics tables)
  |-- StaticPlugin  (serves static files)
        |-- Component  (UI custom element)
        |-- Theme      (CSS theme)
        |-- UI         (HTML + JS app shell)
"""

from __future__ import annotations

import abc
import dataclasses
import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

from shenas_pipes.core.base_auth import PipeAuth
from shenas_pipes.core.base_config import PipeConfig
from shenas_pipes.core.store import DataclassStore

logger = logging.getLogger("shenas.pipes")


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Plugin(abc.ABC):
    """Base for all plugin kinds."""

    name: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str] = ""
    internal: ClassVar[bool] = False

    @property
    def version(self) -> str | None:
        """Installed package version."""
        try:
            from importlib.metadata import version

            return version(f"shenas-{self._kind}-{self.name}")
        except Exception:
            return None

    @property
    def _kind(self) -> str:
        """Plugin kind string for package naming."""
        return "plugin"

    @property
    def commands(self) -> list[str]:
        return []

    def get_info(self) -> dict[str, Any]:
        """Full plugin metadata for API responses."""
        from app.db import get_plugin_state

        state = get_plugin_state(self._kind, self.name)
        return {
            "name": self.name,
            "display_name": self.display_name,
            "kind": self._kind,
            "version": self.version,
            "description": self.description,
            "enabled": state["enabled"] if state else True,
            "added_at": state["added_at"] if state else None,
            "updated_at": state["updated_at"] if state else None,
            "status_changed_at": state["status_changed_at"] if state else None,
            "synced_at": state["synced_at"] if state else None,
        }


# ---------------------------------------------------------------------------
# Pipe
# ---------------------------------------------------------------------------


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

    # Populated by __init__
    _config_store: DataclassStore
    _auth_store: DataclassStore

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        # Auto-set __table__ on inner Config/Auth classes
        if cls.Config is not PipeConfig and not hasattr(cls.Config, "__table__"):
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
    def commands(self) -> list[str]:
        cmds = ["sync"]
        if self.has_auth:
            cmds.append("auth")
        return cmds

    def get_info(self) -> dict[str, Any]:
        return {
            **super().get_info(),
            "has_auth": self.is_authenticated,
            "sync_frequency": self.sync_frequency,
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

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Default sync: build_client -> resources -> run_sync -> transform."""
        from shenas_pipes.core.cli import run_sync

        client = self.build_client()
        res = self.resources(client)
        run_sync(self.name, self.name, res, full_refresh, self._auto_transform)

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


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class Schema(Plugin):
    """Canonical metrics schema."""

    _kind = "schema"
    all_tables: ClassVar[list[type]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "all_tables"):
            cls.tables = [t.__table__ for t in cls.all_tables]

    @classmethod
    def ensure(cls, con: Any) -> None:
        from shenas_schemas.core.ddl import ensure_schema

        ensure_schema(con, all_tables=cls.all_tables)

    @classmethod
    def metadata(cls) -> list[dict[str, Any]]:
        from shenas_schemas.core.introspect import schema_metadata

        return schema_metadata(all_tables=cls.all_tables)


# ---------------------------------------------------------------------------
# Static plugins
# ---------------------------------------------------------------------------


class StaticPlugin(Plugin):
    """Plugin that serves static files (JS/CSS/HTML)."""

    static_dir: ClassVar[Path]


class Component(StaticPlugin):
    """UI component (custom element)."""

    _kind = "component"
    tag: ClassVar[str]
    entrypoint: ClassVar[str]


class Theme(StaticPlugin):
    """CSS theme."""

    _kind = "theme"
    css: ClassVar[str]


class UI(StaticPlugin):
    """UI shell (HTML + JS app shell)."""

    _kind = "ui"
    html: ClassVar[str]
    entrypoint: ClassVar[str]


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
