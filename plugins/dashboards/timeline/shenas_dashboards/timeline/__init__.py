from pathlib import Path

from shenas_dashboards.core import Dashboard


class TimelineComponent(Dashboard):
    name = "timeline"
    display_name = "Timeline"
    description = "Unified timeline showing events and daily metrics from all sources"
    static_dir = Path(__file__).parent / "static"
    tag = "shenas-timeline"
    entrypoint = "timeline.js"
