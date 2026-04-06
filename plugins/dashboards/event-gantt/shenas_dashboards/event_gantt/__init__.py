from pathlib import Path

from shenas_dashboards.core import Dashboard


class EventGanttComponent(Dashboard):
    name = "event-gantt"
    display_name = "Events"
    description = "Timeline visualization for events from all sources"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-event-gantt"
    entrypoint = "event-gantt.js"
