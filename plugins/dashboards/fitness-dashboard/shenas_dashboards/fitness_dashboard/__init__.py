from pathlib import Path

from shenas_dashboards.core import Dashboard


class FitnessDashboardComponent(Dashboard):
    name = "fitness-dashboard"
    display_name = "Fitness Dashboard"
    description = "Canonical fitness metrics dashboard with HRV, sleep, vitals, and body charts"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-dashboard"
    entrypoint = "fitness-dashboard.js"
