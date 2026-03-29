from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-ui-default")
except Exception:
    _version = "dev"

UI = {
    "name": "default",
    "version": _version,
    "description": "Default shenas UI shell with navigation, plugin host, and status overview",
    "static_dir": Path(__file__).parent / "static",
    "entrypoint": "default.js",
    "html": "default.html",
}
