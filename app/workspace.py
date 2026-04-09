"""Workspace state persistence: a JSON blob per named workspace.

Lives in each user's encrypted DB; not keyed by user_id.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Workspace(Table):
    """Workspace state (tab layout, active tab, ...)."""

    class _Meta:
        name = "workspace"
        display_name = "Workspace"
        description = "Per-workspace state (tab layout, active tab, ...)."
        schema = "shenas_system"
        pk = ("workspace_id",)

    workspace_id: Annotated[int, Field(db_type="INTEGER", description="Workspace ID")] = 1
    state: Annotated[str, Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'")] = "{}"
    updated_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
    ) = None

    @classmethod
    def get(cls, workspace_id: int = 1) -> dict[str, Any]:
        """Return the JSON-decoded state for ``workspace_id``, or empty."""
        row = cls.find(workspace_id)
        if row is None or not row.state:
            return {}
        try:
            return json.loads(row.state)
        except Exception:
            return {}

    @classmethod
    def put(cls, state: dict[str, Any], workspace_id: int = 1) -> None:
        """Upsert the JSON-encoded state for ``workspace_id``."""
        cls(
            workspace_id=workspace_id,
            state=json.dumps(state),
            updated_at=_now_iso(),
        ).upsert()
