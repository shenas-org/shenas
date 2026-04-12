"""Theme plugin ABC."""

from __future__ import annotations

from typing import ClassVar

from app.static_plugin import StaticPlugin


class Theme(StaticPlugin):
    """CSS theme. Only one active at a time (managed by PluginInstance)."""

    _kind = "theme"
    enabled_by_default: ClassVar[bool] = False
    single_active: ClassVar[bool] = True
    css: ClassVar[str]
