"""Workspace state persistence: a single-row JSON blob."""

from __future__ import annotations

import json
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table


class Workspace(Table):
    """App workspace state (tab layout, active tab, etc.).

    Single-row config table: the entire workspace state is JSON-encoded
    into the ``state`` column. Reads / writes go through the ABC's
    single-row helpers (``read_value`` / ``write_row``); ``get`` and
    ``save`` are thin convenience views that handle the JSON layer.
    """

    table_name: ClassVar[str] = "workspace"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Workspace"
    table_description: ClassVar[str | None] = "Single-row workspace state (tab layout, active tab, ...)."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    state: Annotated[str, Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'")] = "{}"
    updated_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
    ) = None

    @classmethod
    def get(cls) -> dict[str, Any]:
        raw = cls.read_value("state")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    @classmethod
    def put(cls, state: dict[str, Any]) -> None:
        cls.write_row(state=json.dumps(state))
