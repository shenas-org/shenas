from pathlib import Path

try:
    from importlib.metadata import version

    _version = version("shenas-component-data-table")
except Exception:
    _version = "dev"

COMPONENT = {
    "name": "data-table",
    "version": _version,
    "description": "Data table with filtering, sorting, pagination, and column resizing",
    "static_dir": Path(__file__).parent / "static",
    "tag": "shenas-data-table",
    "entrypoint": "data-table.js",
    "html": "data-table.html",
}
