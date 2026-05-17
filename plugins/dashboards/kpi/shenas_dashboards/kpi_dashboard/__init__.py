from pathlib import Path

from shenas_dashboards.core import Dashboard


class KpiDashboardComponent(Dashboard):
    name = "kpi"
    display_name = "KPI"
    description = (
        "Paperclip KPI dashboard — cycle time, lead time, WIP, cost, rework rate, stranded issues, "
        "decision queue, blocker chains, approval latency, and throughput vs. spend"
    )
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-kpi-dashboard"
    entrypoint = "kpi-dashboard.js"
