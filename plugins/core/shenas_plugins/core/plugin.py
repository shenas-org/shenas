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

    def enable(self) -> str:
        """Enable this plugin."""
        from app.db import upsert_plugin_state

        upsert_plugin_state(self._kind, self.name, enabled=True)
        return f"Enabled {self._kind} {self.name}"

    def disable(self) -> str:
        """Disable this plugin."""
        from app.db import upsert_plugin_state

        upsert_plugin_state(self._kind, self.name, enabled=False)
        return f"Disabled {self._kind} {self.name}"

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


class _SelectOneMixin:
    """Mixin for plugin kinds where only one can be active at a time."""

    enabled_by_default: ClassVar[bool] = False

    def enable(self) -> str:
        """Select this plugin, deselecting all others of the same kind."""
        from app.db import get_all_plugin_states, upsert_plugin_state

        for state in get_all_plugin_states(self._kind):
            if state["name"] != self.name and state["enabled"]:
                upsert_plugin_state(self._kind, state["name"], enabled=False)
        upsert_plugin_state(self._kind, self.name, enabled=True)
        return f"Selected {self._kind} {self.name}"

    def disable(self) -> str:
        """Deselect this plugin, falling back to 'default'."""
        from app.db import upsert_plugin_state

        if self.name == "default":
            return f"Cannot deselect the default {self._kind}"
        upsert_plugin_state(self._kind, self.name, enabled=False)
        upsert_plugin_state(self._kind, "default", enabled=True)
        return f"Switched {self._kind} to default"
