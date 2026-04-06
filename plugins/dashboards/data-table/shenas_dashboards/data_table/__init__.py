from pathlib import Path

from shenas_dashboards.core import Dashboard


class DataTableComponent(Dashboard):
    name = "data-table"
    display_name = "Data Table"
    description = "Data table with filtering, sorting, pagination, and column resizing"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-data-table"
    entrypoint = "data-table.js"
