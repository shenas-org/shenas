"""StaticPlugin ABC."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from app.plugin import Plugin

if TYPE_CHECKING:
    from pathlib import Path


class StaticPlugin(Plugin):
    """Plugin that serves static files (JS/CSS/HTML)."""

    static_dir: ClassVar[Path]
