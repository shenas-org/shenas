"""Workspace state persistence: a JSON blob for the current user's layout.

Lives in each user's encrypted DB; not keyed by user_id.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from shenas_plugins.core.table import Field, SingletonTable


@dataclass
class Workspace(SingletonTable):
    """Workspace state (tab layout, active tab, ...)."""

    class _Meta:
        name = "workspace"
        display_name = "Workspace"
        description = "Workspace state (tab layout, active tab, ...)."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Singleton row ID", db_default="1")] = 1
    state: Annotated[
        str,
        Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'"),
    ] = "{}"
