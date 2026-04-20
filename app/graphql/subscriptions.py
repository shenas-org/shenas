"""GraphQL subscription resolvers.

Each subscription wraps a topic from :mod:`app.pubsub` and yields
typed payloads to connected WebSocket clients. See
``docs/graphql-subscriptions.md`` for the architecture.
"""

from __future__ import annotations

from collections.abc import AsyncIterator  # noqa: TC003 -- runtime: strawberry inspects return annotations

import strawberry


@strawberry.type
class EntityChangedPayload:
    """Notification that an entity was created, updated, or received new statements."""

    uuid: str
    type: str = ""
    name: str = ""


@strawberry.type
class TableChangedPayload:
    """Notification that a table's data was modified (sync, transform, flush)."""

    schema_name: str
    table: str


@strawberry.type
class PluginStateChangedPayload:
    """Notification that a plugin's state changed (synced, enabled, disabled)."""

    kind: str
    name: str
    synced_at: str | None = None
    enabled: bool | None = None


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def entity_changed(self) -> AsyncIterator[EntityChangedPayload]:
        """Fires when an entity is created, updated, or gains new statements."""
        from app.pubsub import pubsub

        async for event in pubsub.subscribe("entity_changed"):
            yield EntityChangedPayload(
                uuid=event.get("uuid", ""),
                type=event.get("type", ""),
                name=event.get("name", ""),
            )

    @strawberry.subscription
    async def table_data_changed(self, schema_name: str | None = None) -> AsyncIterator[TableChangedPayload]:
        """Fires when table data changes. Optionally filter by schema."""
        from app.pubsub import pubsub

        async for event in pubsub.subscribe("table_data_changed"):
            if schema_name is None or event.get("schema") == schema_name:
                yield TableChangedPayload(
                    schema_name=event.get("schema", ""),
                    table=event.get("table", ""),
                )

    @strawberry.subscription
    async def plugin_state_changed(self, kind: str | None = None) -> AsyncIterator[PluginStateChangedPayload]:
        """Fires when a plugin is synced, enabled, or disabled. Optionally filter by kind."""
        from app.pubsub import pubsub

        async for event in pubsub.subscribe("plugin_state_changed"):
            if kind is None or event.get("kind") == kind:
                yield PluginStateChangedPayload(
                    kind=event.get("kind", ""),
                    name=event.get("name", ""),
                    synced_at=event.get("synced_at"),
                    enabled=event.get("enabled"),
                )
