"""Source access type descriptors.

Each ``AccessType`` instance describes how a source plugin accesses its
data. Sources declare one or more access types via ``access_types``.
The class carries metadata (label, icon, description) that the UI
renders, and can be extended with behavior (e.g. auth requirements,
rate-limit strategies) in the future.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccessType:
    """Describes how a source plugin accesses its upstream data."""

    name: str
    label: str
    icon: str  # short text/emoji-free icon identifier for the frontend
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "label": self.label, "icon": self.icon, "description": self.description}


# -- Instances (importable by source plugins) ----------------------------------

OFFICIAL_API = AccessType(
    name="official_api",
    label="Official API",
    icon="official_api",
    description="Uses a documented, supported API with developer access.",
)

UNOFFICIAL_API = AccessType(
    name="unofficial_api",
    label="Unofficial API",
    icon="unofficial_api",
    description="Uses a reverse-engineered or undocumented API.",
)

LOCAL_FILES = AccessType(
    name="local_files",
    label="Local Files",
    icon="local_files",
    description="Reads from local filesystem (notes, config, etc.).",
)

LOCAL_DB = AccessType(
    name="local_db",
    label="Local Database",
    icon="local_db",
    description="Reads from a local database (browser SQLite, etc.).",
)

CLOUD_IMPORT = AccessType(
    name="cloud_import",
    label="Cloud Import",
    icon="cloud_import",
    description="Downloads from cloud storage (Google Drive, etc.).",
)

EXPORT_FILE = AccessType(
    name="export_file",
    label="Export File",
    icon="export_file",
    description="Parses user-exported files (mbox, CSV, JSON, etc.).",
)

SCRAPING = AccessType(
    name="scraping",
    label="Web Scraping",
    icon="scraping",
    description="Extracts data from web pages via HTML scraping.",
)

PUBLIC_DATASET = AccessType(
    name="public_dataset",
    label="Public Dataset",
    icon="public_dataset",
    description="Downloads publicly available open data.",
)

ALL_ACCESS_TYPES = {
    at.name: at
    for at in (OFFICIAL_API, UNOFFICIAL_API, LOCAL_FILES, LOCAL_DB, CLOUD_IMPORT, EXPORT_FILE, SCRAPING, PUBLIC_DATASET)
}
