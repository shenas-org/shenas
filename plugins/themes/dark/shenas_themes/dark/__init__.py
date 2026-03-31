from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-theme-dark")
except Exception:
    _version = "dev"

THEME = {
    "name": "dark",
    "display_name": "Dark",
    "version": _version,
    "description": "Dark mode theme with muted colors and dark backgrounds",
    "static_dir": Path(__file__).parent / "static",
    "css": "dark.css",
}
