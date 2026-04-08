"""Workspace state persistence."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, UserTable


class Workspace:
    """App workspace state (tab layout, active tab, etc.) per user."""

    class _Table(UserTable):
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

    @staticmethod
    def get(user_id: int = 0, workspace_id: int = 1) -> dict[str, Any]:
        import json

        rows = Workspace._Table.read_rows(user_id)
        row = next((r for r in rows if r["workspace_id"] == workspace_id), None)
        if not row:
            return {}
        try:
            return json.loads(row["state"])
        except Exception:
            return {}

    @staticmethod
    def save(state: dict[str, Any], user_id: int = 0, workspace_id: int = 1) -> None:
        import json
        from datetime import datetime, timezone

        Workspace._Table.upsert_row(
            user_id,
            workspace_id=workspace_id,
            state=json.dumps(state),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
