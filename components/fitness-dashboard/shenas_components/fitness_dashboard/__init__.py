from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-component-fitness-dashboard")
except Exception:
    _version = "dev"

COMPONENT = {
    "name": "fitness-dashboard",
    "version": _version,
    "description": "Canonical fitness metrics dashboard with HRV, sleep, vitals, and body charts",
    "static_dir": Path(__file__).parent / "static",
    "tag": "shenas-dashboard",
    "entrypoint": "fitness-dashboard.js",
}
