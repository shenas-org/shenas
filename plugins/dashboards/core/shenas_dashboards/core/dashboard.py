"""Dashboard plugin ABC."""

from __future__ import annotations

from typing import ClassVar

from app.static_plugin import StaticPlugin


class Dashboard(StaticPlugin):
    """UI component (custom element)."""

    _kind = "dashboard"
    tag: ClassVar[str]
    entrypoint: ClassVar[str]
