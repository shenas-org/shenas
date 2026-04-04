from pathlib import Path

from shenas_pipes.core.abc import UI


class DefaultUI(UI):
    name = "default"
    display_name = "Default UI"
    description = "Default shenas UI shell with navigation, plugin host, and status overview"
    internal = True
    static_dir = Path(__file__).parent / "static"
    entrypoint = "default.js"
    html = "default.html"
