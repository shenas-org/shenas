from pathlib import Path

from shenas_dashboards.core import Dashboard


class FitnessDashboardComponent(Dashboard):
    name = "fitness"
    display_name = "Fitness"
    description = "Canonical fitness metrics dashboard with HRV, sleep, vitals, and body charts"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-dashboard"
    entrypoint = "fitness-dashboard.js"
