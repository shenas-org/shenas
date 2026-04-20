from typing import ClassVar

from app.table import Field
from shenas_datasets.core.dataset import Dataset
from shenas_datasets.events.metrics import ALL_TABLES, Event


class EventsSchema(Dataset):
    name = "events"
    display_name = "Events"
    description = "Unified event timeline: calendar, music, workouts, and more"
    all_tables = ALL_TABLES
    primary_table = "events"
    entity_types: ClassVar[list[str]] = ["human"]


ensure_schema = EventsSchema.ensure

__all__ = [
    "ALL_TABLES",
    "Event",
    "EventsSchema",
    "Field",
    "ensure_schema",
]
