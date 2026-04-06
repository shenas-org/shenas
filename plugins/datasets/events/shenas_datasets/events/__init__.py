from shenas_datasets.core import Field, MetricProvider, generate_ddl, table_metadata
from shenas_datasets.core.dataset import Dataset
from shenas_datasets.events.metrics import ALL_TABLES, Event


class EventsSchema(Dataset):
    name = "events"
    display_name = "Events"
    description = "Unified event timeline: calendar, music, workouts, and more"
    all_tables = ALL_TABLES
    primary_table = "events"


ensure_schema = EventsSchema.ensure

__all__ = [
    "ALL_TABLES",
    "Event",
    "EventsSchema",
    "Field",
    "MetricProvider",
    "ensure_schema",
    "generate_ddl",
    "table_metadata",
]
