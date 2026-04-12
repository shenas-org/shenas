from app.table import Field
from shenas_datasets.core.dataset import Dataset
from shenas_datasets.location.metrics import ALL_TABLES, LocationVisit


class LocationSchema(Dataset):
    name = "location"
    display_name = "Location"
    description = "Geofence-categorized location visits"
    all_tables = ALL_TABLES
    primary_table = "location_visits"


ensure_schema = LocationSchema.ensure

__all__ = [
    "ALL_TABLES",
    "Field",
    "LocationSchema",
    "LocationVisit",
    "ensure_schema",
]
