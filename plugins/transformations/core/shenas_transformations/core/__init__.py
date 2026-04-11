"""Transform plugin ABC and TransformConfig base."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.plugin import Plugin
from shenas_plugins.core.table import Field, SingletonTable


@dataclass
class TransformConfig(SingletonTable):
    """Base configuration for transform plugins.

    Transforms that need persistent config (API keys, model names, etc.)
    subclass this. ``Transform.__init_subclass__`` auto-sets the
    ``_Meta.name`` to ``transform_{plugin_name}`` so each plugin gets
    its own table in the ``config`` schema.
    """

    _abstract: ClassVar[bool] = True

    class _Meta(SingletonTable._Meta):
        display_name = "Transform Config"
        description = "Per-transform-plugin configuration."
        pk = ("id",)
        schema = "config"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if "_abstract" not in cls.__dict__:
            cls._abstract = True
        super().__init_subclass__(**kwargs)

    id: Annotated[int, Field(db_type="INTEGER", description="Config row")] = 1


class Transform(Plugin):
    """Base class for transform plugins.

    A transform plugin defines a *type* of data transformation
    (SQL, geofence, geocode, LLM categorize, etc.). Each type can
    have multiple configured instances (rows in
    ``shenas_system.transform_instances``).
    """

    _kind = "transformation"

    Config: ClassVar[type] = TransformConfig

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        if cls.Config is not TransformConfig:
            meta = getattr(cls.Config, "_Meta", None)
            if meta and not getattr(meta, "name", None):
                cls.Config._Meta = type("_Meta", (meta,), {"name": f"transform_{cls.name}"})  # ty: ignore[invalid-assignment]
                cls.Config._abstract = False  # ty: ignore[invalid-assignment]

    @property
    def has_config(self) -> bool:
        return self.Config is not TransformConfig

    @property
    def has_data(self) -> bool:
        return True

    @abc.abstractmethod
    def execute(
        self,
        con: Any,
        instance: Any,
        *,
        device_id: str = "local",
    ) -> int:
        """Execute one transform instance. Returns 1 on success, 0 on failure."""
        ...

    def validate_params(self, params: dict[str, Any]) -> None:
        """Validate type-specific params before saving. Raise ValueError on invalid."""

    def param_schema(self) -> list[dict[str, Any]]:
        """Describe accepted params for UI form generation."""
        return []

    def seed_defaults_for_source(self, source_name: str) -> None:
        """Seed default transform instances for a given source plugin."""

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["param_schema"] = self.param_schema()
        return info


__all__ = [
    "Transform",
    "TransformConfig",
]
