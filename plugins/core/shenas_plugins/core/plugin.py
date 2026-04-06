"""Base Plugin ABC and _SelectOneMixin."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.field import Field


class Plugin(abc.ABC):
    """Base for all plugin kinds."""

    @dataclass
    class _Row:
        __table__: ClassVar[str] = "plugins"
        __pk__: ClassVar[tuple[str, ...]] = ("kind", "name")

        kind: Annotated[str, Field(db_type="VARCHAR", description="Plugin kind")] = ""
        name: Annotated[str, Field(db_type="VARCHAR", description="Plugin name")] = ""
        enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] = True
        added_at: (
            Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None
        ) = None
        updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
        status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None
        synced_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last synced")] | None = None

    name: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str] = ""
    internal: ClassVar[bool] = False
    enabled_by_default: ClassVar[bool] = True

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
    def has_config(self) -> bool:
        return False

    @property
    def has_data(self) -> bool:
        return False

    @property
    def has_auth(self) -> bool:
        return False

    def get_config_entries(self) -> list[dict[str, str | None]]:
        return []

    def set_config_value(self, key: str, value: str | None) -> None:  # noqa: B027
        """Set a config value. Override in subclasses with config."""

    def get_config_value(self, key: str) -> Any | None:  # noqa: ARG002
        return None

    def delete_config(self) -> None:  # noqa: B027
        """Delete all config. Override in subclasses with config."""

    @property
    def commands(self) -> list[str]:
        return []

    # -- State management --

    @property
    def state(self) -> dict[str, Any] | None:
        """Load plugin state from the database. Returns None if not tracked."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
                "FROM shenas_system.plugins WHERE kind = ? AND name = ?",
                [self._kind, self.name],
            ).fetchone()
        if not row:
            return None
        return {
            "kind": row[0],
            "name": row[1],
            "enabled": row[2],
            "added_at": str(row[3]) if row[3] else None,
            "updated_at": str(row[4]) if row[4] else None,
            "status_changed_at": str(row[5]) if row[5] else None,
            "synced_at": str(row[6]) if row[6] else None,
        }

    @property
    def enabled(self) -> bool:
        """Whether this plugin is enabled."""
        s = self.state
        return s["enabled"] if s else self.enabled_by_default

    def save_state(self, *, enabled: bool) -> None:
        """Create or update this plugin's state in the database."""
        from app.db import cursor

        now = "current_timestamp"
        with cursor() as cur:
            row = cur.execute(
                "SELECT enabled FROM shenas_system.plugins WHERE kind = ? AND name = ?",
                [self._kind, self.name],
            ).fetchone()
            if row is not None:
                if enabled != row[0]:
                    cur.execute(
                        f"UPDATE shenas_system.plugins SET enabled = ?, status_changed_at = {now}, updated_at = {now} "
                        "WHERE kind = ? AND name = ?",
                        [enabled, self._kind, self.name],
                    )
                else:
                    cur.execute(
                        f"UPDATE shenas_system.plugins SET updated_at = {now} WHERE kind = ? AND name = ?",
                        [self._kind, self.name],
                    )
            else:
                cur.execute(
                    f"INSERT INTO shenas_system.plugins (kind, name, enabled, added_at, status_changed_at) "
                    f"VALUES (?, ?, ?, {now}, {now})",
                    [self._kind, self.name, enabled],
                )

    def remove_state(self) -> None:
        """Remove this plugin's state from the database."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.plugins WHERE kind = ? AND name = ?", [self._kind, self.name])

    def mark_synced(self) -> None:
        """Update the synced_at timestamp. Creates the state row if missing."""
        from app.db import cursor

        with cursor() as cur:
            row = cur.execute(
                "SELECT 1 FROM shenas_system.plugins WHERE kind = ? AND name = ?",
                [self._kind, self.name],
            ).fetchone()
        if not row:
            self.save_state(enabled=True)
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.plugins SET synced_at = current_timestamp, updated_at = current_timestamp "
                "WHERE kind = ? AND name = ?",
                [self._kind, self.name],
            )

    def enable(self) -> str:
        """Enable this plugin."""
        self.save_state(enabled=True)
        return f"Enabled {self._kind} {self.name}"

    def disable(self) -> str:
        """Disable this plugin."""
        self.save_state(enabled=False)
        return f"Disabled {self._kind} {self.name}"

    def get_info(self) -> dict[str, Any]:
        """Full plugin metadata for API responses."""
        s = self.state
        return {
            "name": self.name,
            "display_name": self.display_name,
            "kind": self._kind,
            "version": self.version,
            "description": self.description,
            "has_config": self.has_config,
            "has_data": self.has_data,
            "has_auth": self.has_auth,
            "enabled": s["enabled"] if s else self.enabled_by_default,
            "added_at": s["added_at"] if s else None,
            "updated_at": s["updated_at"] if s else None,
            "status_changed_at": s["status_changed_at"] if s else None,
            "synced_at": s["synced_at"] if s else None,
        }


class _SelectOneMixin:
    """Mixin for plugin kinds where only one can be active at a time."""

    enabled_by_default: ClassVar[bool] = False

    def enable(self) -> str:
        """Select this plugin, deselecting all others of the same kind."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.plugins SET enabled = false, "
                "status_changed_at = current_timestamp, updated_at = current_timestamp "
                "WHERE kind = ? AND name != ? AND enabled = true",
                [self._kind, self.name],
            )
        self.save_state(enabled=True)
        return f"Selected {self._kind} {self.name}"

    def disable(self) -> str:
        """Deselect this plugin, falling back to 'default'."""
        if self.name == "default":
            return f"Cannot deselect the default {self._kind}"
        self.save_state(enabled=False)
        # Enable the default plugin of this kind
        from app.db import cursor

        now = "current_timestamp"
        with cursor() as cur:
            row = cur.execute(
                "SELECT 1 FROM shenas_system.plugins WHERE kind = ? AND name = 'default'",
                [self._kind],
            ).fetchone()
            if row:
                cur.execute(
                    f"UPDATE shenas_system.plugins SET enabled = true, status_changed_at = {now}, updated_at = {now} "
                    "WHERE kind = ? AND name = 'default'",
                    [self._kind],
                )
            else:
                cur.execute(
                    f"INSERT INTO shenas_system.plugins (kind, name, enabled, added_at, status_changed_at) "
                    f"VALUES (?, 'default', true, {now}, {now})",
                    [self._kind],
                )
        return f"Switched {self._kind} to default"
