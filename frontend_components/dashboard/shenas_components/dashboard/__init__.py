from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-component-dashboard")
except Exception:
    _version = "dev"

COMPONENT = {
    "name": "dashboard",
    "version": _version,
    "description": "Canonical metrics dashboard with HRV, sleep, vitals, and body charts",
    "static_dir": Path(__file__).parent / "static",
    "entrypoint": "dashboard.js",
    "html": "dashboard.html",
}
