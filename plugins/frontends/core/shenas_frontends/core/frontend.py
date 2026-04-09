"""Frontend plugin ABC."""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.static import StaticPlugin


class Frontend(StaticPlugin):
    """Frontend shell. Only one active at a time (managed by PluginInstance)."""

    _kind = "frontend"
    enabled_by_default: ClassVar[bool] = False
    single_active: ClassVar[bool] = True
    html: ClassVar[str]
    entrypoint: ClassVar[str]
