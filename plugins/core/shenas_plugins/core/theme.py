"""Theme plugin ABC."""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.plugin import _SelectOneMixin
from shenas_plugins.core.static import StaticPlugin


class Theme(_SelectOneMixin, StaticPlugin):
    """CSS theme. Only one active at a time."""

    _kind = "theme"
    css: ClassVar[str]
