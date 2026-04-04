from shenas_schemas.core import Field, MetricProvider, generate_ddl, table_metadata
from shenas_schemas.core.schema import Schema
from shenas_schemas.events.metrics import ALL_TABLES, Event


class EventsSchema(Schema):
    name = "events"
    display_name = "Events"
    description = "Unified event timeline: calendar, music, workouts, and more"
    all_tables = ALL_TABLES


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
