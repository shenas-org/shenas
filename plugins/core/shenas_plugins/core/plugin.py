"""Base Plugin ABC and _SelectOneMixin."""

from __future__ import annotations

import abc
from typing import Any, ClassVar


class Plugin(abc.ABC):
    """Base for all plugin kinds."""

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
        from app.db import get_plugin_state

        return get_plugin_state(self._kind, self.name)

    @property
    def enabled(self) -> bool:
        """Whether this plugin is enabled."""
        s = self.state
        return s["enabled"] if s else self.enabled_by_default

    def save_state(self, *, enabled: bool) -> None:
        """Create or update this plugin's state in the database."""
        from app.db import upsert_plugin_state

        upsert_plugin_state(self._kind, self.name, enabled=enabled)

    def remove_state(self) -> None:
        """Remove this plugin's state from the database."""
        from app.db import remove_plugin_state

        remove_plugin_state(self._kind, self.name)

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
        from app.db import get_all_plugin_states

        for s in get_all_plugin_states(self._kind):
            if s["name"] != self.name and s["enabled"]:
                self.__class__._upsert(self._kind, s["name"], enabled=False)
        self.save_state(enabled=True)
        return f"Selected {self._kind} {self.name}"

    def disable(self) -> str:
        """Deselect this plugin, falling back to 'default'."""
        if self.name == "default":
            return f"Cannot deselect the default {self._kind}"
        self.save_state(enabled=False)
        self.__class__._upsert(self._kind, "default", enabled=True)
        return f"Switched {self._kind} to default"

    @staticmethod
    def _upsert(kind: str, name: str, *, enabled: bool) -> None:
        from app.db import upsert_plugin_state

        upsert_plugin_state(kind, name, enabled=enabled)
