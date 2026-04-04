from pathlib import Path

from shenas_themes.core import Theme


class DefaultTheme(Theme):
    name = "default"
    display_name = "Default"
    description = "Default shenas theme with system fonts and light colors"
    static_dir = Path(__file__).parent / "static"
    css = "default.css"
