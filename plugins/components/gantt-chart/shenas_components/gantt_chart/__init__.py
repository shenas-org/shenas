from pathlib import Path

from shenas_components.core import Component


class GanttChartComponent(Component):
    name = "gantt-chart"
    display_name = "Events"
    description = "Timeline visualization for events from all sources"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-gantt-chart"
    entrypoint = "gantt-chart.js"
