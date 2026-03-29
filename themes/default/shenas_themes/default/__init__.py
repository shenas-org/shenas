from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-theme-default")
except Exception:
    _version = "dev"

THEME = {
    "name": "default",
    "display_name": "Default",
    "internal": True,
    "version": _version,
    "description": "Default shenas theme with system fonts and light colors",
    "static_dir": Path(__file__).parent / "static",
    "css": "default.css",
}
