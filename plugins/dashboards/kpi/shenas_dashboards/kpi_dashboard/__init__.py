from pathlib import Path

from shenas_dashboards.core import Dashboard


class KpiDashboardComponent(Dashboard):
    name = "kpi"
    display_name = "KPI"
    description = (
        "Paperclip KPI dashboard — cycle time, lead time, WIP, cost, rework rate, stranded issues, and decision queue"
    )
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-kpi-dashboard"
    entrypoint = "kpi-dashboard.js"
