from pathlib import Path

from shenas_plugins.core import Theme


class DarkTheme(Theme):
    name = "dark"
    display_name = "Dark"
    description = "Dark mode theme with muted colors and dark backgrounds"
    static_dir = Path(__file__).parent / "static"
    css = "dark.css"
