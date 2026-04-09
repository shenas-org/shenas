"""Workspace state persistence: a JSON blob per (user, workspace)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, UserTable


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Workspace(UserTable):
    """Per-user workspace state (tab layout, active tab, ...).

    Composite PK is ``(workspace_id, user_id)`` -- a single user can own
    multiple named workspaces; ``user_id`` is 0 in single-user mode.
    The state itself is JSON-encoded into the ``state`` column.
    """

    table_name: ClassVar[str] = "workspace"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Workspace"
    table_description: ClassVar[str | None] = "Per-user workspace state (tab layout, active tab, ...)."
    table_pk: ClassVar[tuple[str, ...]] = ("workspace_id", "user_id")

    workspace_id: Annotated[int, Field(db_type="INTEGER", description="Workspace ID")] = 1
    user_id: Annotated[int, Field(db_type="INTEGER", description="Local user ID (0 = single-user mode)")] = 0
    state: Annotated[str, Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'")] = "{}"
    updated_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
    ) = None

    @classmethod
    def get(cls, user_id: int = 0, workspace_id: int = 1) -> dict[str, Any]:
        """Return the JSON-decoded state for ``(workspace_id, user_id)``, or empty."""
        row = cls.find(workspace_id, user_id)
        if row is None or not row.state:
            return {}
        try:
            return json.loads(row.state)
        except Exception:
            return {}

    @classmethod
    def put(cls, state: dict[str, Any], user_id: int = 0, workspace_id: int = 1) -> None:
        """Upsert the JSON-encoded state for ``(workspace_id, user_id)``."""
        cls(
            workspace_id=workspace_id,
            user_id=user_id,
            state=json.dumps(state),
            updated_at=_now_iso(),
        ).upsert()
