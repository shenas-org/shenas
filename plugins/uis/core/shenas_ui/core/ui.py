"""UI plugin ABC."""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.plugin import _SelectOneMixin
from shenas_plugins.core.static import StaticPlugin


class UI(_SelectOneMixin, StaticPlugin):
    """UI shell. Only one active at a time."""

    _kind = "ui"
    html: ClassVar[str]
    entrypoint: ClassVar[str]
