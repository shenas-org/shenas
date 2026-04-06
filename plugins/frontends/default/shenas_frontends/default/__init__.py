from pathlib import Path

from shenas_frontends.core import Frontend


class DefaultUI(Frontend):
    name = "default"
    display_name = "Default Frontend"
    description = "Default shenas Frontend shell with navigation, plugin host, and status overview"
    static_dir = Path(__file__).parent / "static"
    entrypoint = "default.js"
    html = "default.html"
