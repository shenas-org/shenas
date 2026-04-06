from pathlib import Path

from shenas_frontends.core import Frontend


class FocusUI(Frontend):
    name = "focus"
    display_name = "Focus"
    description = "Single-component view with bottom navigation and hotkey support"
    static_dir = Path(__file__).parent / "static"
    entrypoint = "focus.js"
    html = "focus.html"
