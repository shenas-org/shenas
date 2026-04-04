from pathlib import Path

from shenas_components.core import Component


class FitnessDashboardComponent(Component):
    name = "fitness-dashboard"
    display_name = "Fitness Dashboard"
    description = "Canonical fitness metrics dashboard with HRV, sleep, vitals, and body charts"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-dashboard"
    entrypoint = "fitness-dashboard.js"
