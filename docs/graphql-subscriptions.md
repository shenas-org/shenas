# GraphQL subscriptions: live data-change notifications

Status: proposed. Authors: shenas team.

## Problem

**Stale UI after data changes.** When a sync runs (on this device or
another via mesh), data changes silently: new entity statements, new
table rows, updated plugin state. The frontend has no way to know until
the user navigates away and back or does Ctrl+R.

**Manual refresh orchestration.** Today every mutation and sync hook
manually calls `_fetchInfo()`, `_fetchEntities()`, `_dataRefreshKey++`,
`_refreshDashboards()`, etc. in specific post-action callbacks. Miss one
and the UI stays stale. This refresh tracking is scattered across 10+
components and is the source of most "data doesn't show" bugs.

**Goal: eliminate manual refresh orchestration entirely.** Data changes
publish to a topic; Apollo's normalized cache absorbs the update;
components re-render automatically because their fragment's cache entry
changed. No `_fetchInfo()`, no `_dataRefreshKey`, no conditional
`if (tab === "entities") this._fetchEntities()` -- data just arrives.

## Subscription topics

| Topic | Trigger | Payload | Consumer |
|---|---|---|---|
| `entityChanged` | sync projection, upsertStatement, createEntity, updateEntity | `{ uuid, type, name }` | entities-page graph + detail panel |
| `tableDataChanged` | flush_to_encrypted, transform execution | `{ schema, table }` | data-table component |
| `pluginStateChanged` | sync complete, enable/disable, config save | `{ kind, name, syncedAt?, enabled? }` | sidebar plugin cards |
| `configChanged` | set_config mutation | `{ kind, name, key }` | config-page |

## Backend

### Pub/sub broker

A lightweight in-process pub/sub at `app/pubsub.py`:

```python
class PubSub:
    """In-process async pub/sub for GraphQL subscription topics."""

    async def publish(self, topic: str, payload: dict) -> None: ...
    async def subscribe(self, topic: str) -> AsyncIterator[dict]: ...
```

No external dependency (Redis, NATS). Shenas runs single-process on
localhost. If multi-process deployment becomes relevant later, swap the
in-process broker for Redis pub/sub behind the same interface.

### Subscription resolvers

```python
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def entity_changed(self) -> AsyncIterator[EntityChangedPayload]:
        async for event in pubsub.subscribe("entity_changed"):
            yield EntityChangedPayload(**event)

    @strawberry.subscription
    async def table_data_changed(
        self, schema: str | None = None
    ) -> AsyncIterator[TableChangedPayload]:
        async for event in pubsub.subscribe("table_data_changed"):
            if schema is None or event["schema"] == schema:
                yield TableChangedPayload(**event)
```

### Publishing from mutations / sync hooks

```python
# In Source.sync() post-hooks:
await pubsub.publish("table_data_changed", {"schema": ..., "table": ...})
await pubsub.publish("plugin_state_changed", {"kind": "source", "name": ..., "syncedAt": ...})

# In upsert_statement mutation:
await pubsub.publish("entity_changed", {"uuid": entity_id, "type": ..., "name": ...})
```

For sync code running in threads (not async), use a thread-safe
`publish_sync()` wrapper that schedules onto the event loop.

### Strawberry + FastAPI wiring

```python
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)
graphql_app = GraphQLRouter(
    schema,
    subscription_protocols=["graphql-transport-ws"],
)
```

Strawberry handles the WebSocket upgrade at the same `/api/graphql` path.

## Frontend

### Apollo WebSocket link

Add `graphql-ws` to `app/vendor/package.json` and configure a split
link in `apollo.ts`:

```typescript
import { GraphQLWsLink } from "@apollo/client/link/subscriptions";
import { createClient } from "graphql-ws";
import { split, HttpLink } from "@apollo/client/core";
import { getMainDefinition } from "@apollo/client/utilities";

const wsLink = new GraphQLWsLink(
  createClient({ url: `ws://${location.host}/api/graphql` })
);
const httpLink = new HttpLink({ uri: "/api/graphql" });

const link = split(
  ({ query }) => {
    const def = getMainDefinition(query);
    return def.kind === "OperationDefinition" && def.operation === "subscription";
  },
  wsLink,
  httpLink,
);
```

### Consuming in Lit components

```typescript
connectedCallback() {
  super.connectedCallback();
  this._sub = this._client.subscribe({
    query: ENTITY_CHANGED_SUBSCRIPTION,
  }).subscribe({
    next: ({ data }) => {
      // Phase 1-3: refetch the affected query
      this._entitiesQuery.refetch();
      // Phase 5: write directly to cache (no round-trip)
      // cache.writeFragment({ ... });
    },
  });
}

disconnectedCallback() {
  this._sub?.unsubscribe();
  super.disconnectedCallback();
}
```

## What subscriptions are NOT for

- **Sync progress** -- stays as SSE (stream of log strings tied to the
  HTTP response body of the sync POST).
- **Telemetry log/span streaming** -- stays as EventSource SSE.
  High-volume, append-only, no cache update needed.
- **Command execution** -- stays as REST POST with SSE response body.

## Rollout phases

| Phase | Scope | Risk |
|---|---|---|
| 1 | `app/pubsub.py` broker + Subscription type + `entityChanged` topic. Wire into entity mutations. Frontend: entities-page subscribes and refetches. | Low |
| 2 | `tableDataChanged` topic. Wire into flush_to_encrypted and transforms. Data-table component subscribes and bumps refreshKey. | Low |
| 3 | `pluginStateChanged` topic. Wire into sync completion + enable/disable. Sidebar cards update live. | Low |
| 4 | Apollo WebSocket link with split routing. Persistent WS connection. | Medium |
| 5 | Cache-first updates: subscription payloads write directly to Apollo cache via writeFragment. Delete all manual `_fetchInfo()` / `_dataRefreshKey++` / `_fetchEntities()` refresh calls. | Medium |

## Open questions

- Should the PubSub broker persist missed events for reconnecting
  clients? (Probably not for v1 -- reconnecting clients refetch.)
- Should subscriptions carry full objects or just notifications to
  refetch? (Start with notification-to-refetch; evolve to full payload
  in Phase 5.)
- Should the WS connection require the same session auth as HTTP?
  (Yes -- pass session token as connectionParams init payload.)
