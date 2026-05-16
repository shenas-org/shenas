from pathlib import Path

from shenas_dashboards.core import Dashboard


class KpiDashboardComponent(Dashboard):
    name = "kpi"
    display_name = "KPI"
    description = "Paperclip KPI dashboard — rework rate per agent, stranded issues, and decision queue depth"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-kpi-dashboard"
    entrypoint = "kpi-dashboard.js"
