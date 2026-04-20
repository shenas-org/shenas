# GraphQL architecture: fragments, cache normalization, and type derivation

Status: proposed. Authors: shenas team.

## Why this document exists

The GraphQL layer has grown organically to 40 Strawberry types, 38 queries,
and 53 mutations on the backend, with 16 queries and 41 mutations on the
frontend. Three structural problems need addressing:

1. **Monolithic init query.** `GET_APP_DATA` fetches 8 plugin kinds +
   dashboards + hotkeys + workspace + theme + device name in one shot on
   every page load. Components that need one plugin's data re-fetch the
   entire response because there's no fragment-level caching.

2. **Zero fragments.** Apollo supports Relay-style fragment composition
   (`useFragment`, fragment spreads) but the codebase uses none. Every
   query inlines its full field set, leading to duplication (e.g.
   `DataResourceType` fields repeated 4+ times) and over-fetching.

3. **Duplicate type definitions.** 40 hand-written `@strawberry.type`
   classes mirror Python `Table` dataclasses field-by-field. Changes to a
   Table's columns require updating both the dataclass and the Strawberry
   type, and they drift silently.

## 1. Fragment convention

Every Lit component that consumes GraphQL data declares a **named
fragment** on the type it needs. Page-level queries compose these
fragments via `...spread`.

```graphql
# Declared by <plugin-card> component
fragment PluginCard on PluginInfo {
  name
  displayName
  enabled
  kind
}

# Declared by <plugin-detail> component
fragment PluginDetail on PluginInfo {
  ...PluginCard
  version
  description
  syncedAt
  hasAuth
  isAuthenticated
  tables
}

# Page query for the sidebar (composes only what it needs)
query Sidebar {
  sources: plugins(kind: "source") { ...PluginCard }
  datasets: plugins(kind: "dataset") { ...PluginCard }
}

# Page query for plugin detail page
query PluginDetailPage($kind: String!, $name: String!) {
  pluginInfo(kind: $kind, name: $name) { ...PluginDetail }
}
```

### Convention rules

- Fragment files live next to the component that owns them:
  `src/plugin-card.fragment.ts`
- Fragments are exported as `gql` tagged template literals
- Page-level query files import and compose fragments
- One fragment per component, named `<ComponentName>` on the relevant
  GraphQL type

## 2. Init query split

Replace the monolithic `GET_APP_DATA` with three lazy-loaded tiers:

| Tier | When fetched | What |
|---|---|---|
| **Shell** | App mount (blocking) | `pluginKinds`, `dashboards`, `theme`, `deviceName` |
| **Sidebar** | Shell rendered (non-blocking) | `plugins(kind: X) { ...PluginCard }` per sidebar kind |
| **Detail** | On navigation | `pluginInfo(kind, name) { ...PluginDetail }` + tab-specific data |

`hotkeys` and `workspace` move to their own queries, fetched lazily when
the settings page is opened.

## 3. Apollo cache normalization

Configure `InMemoryCache` with `typePolicies` so the cache deduplicates
objects by identity:

```typescript
new InMemoryCache({
  typePolicies: {
    PluginInfo: { keyFields: ["kind", "name"] },
    Entity: { keyFields: ["uuid"] },
    EntityType: { keyFields: ["name"] },
    Transform: { keyFields: ["id"] },
    DataResource: { keyFields: ["schema", "table"] },
    Property: { keyFields: ["id"] },
    CategorySet: { keyFields: ["id"] },
  },
})
```

This means:
- A `PluginCard` fragment fetch in the sidebar populates the cache entry
  for that plugin.
- When `PluginDetail` is fetched later, Apollo merges the new fields into
  the same cache entry.
- `watchFragment` lets components subscribe to just their fragment,
  re-rendering only when those fields change.

## 4. Auto-derive GraphQL types from Table classes

Add a helper that generates a `@strawberry.type` from a `Table` subclass
at import time, using `_Meta` + dataclass field annotations:

```python
# app/graphql/derive.py
def gql_type_from_table(
    table_cls: type[Table],
    *,
    name: str | None = None,
    exclude: set[str] = frozenset(),
) -> type:
    """Generate a @strawberry.type from a Table subclass.

    Reads _Meta.name, _Meta.display_name, _Meta.description and the
    dataclass fields + their Field annotations (db_type, description,
    display_name). Excludes internal fields (_dlt_*, id if auto-PK).
    """
```

Mapping `db_type` to GraphQL scalar:

| DuckDB type | GraphQL scalar |
|---|---|
| `VARCHAR`, `TEXT` | `str` |
| `INTEGER`, `BIGINT` | `int` |
| `DOUBLE`, `FLOAT` | `float` |
| `BOOLEAN` | `bool` |
| `TIMESTAMP`, `DATE` | `str` (ISO format) |
| `JSON` | `strawberry.scalars.JSON` |
| Nullable | `Optional[T]` |

Usage:

```python
from app.graphql.derive import gql_type_from_table
from app.entity import Entity, EntityType, EntityRelationshipType

GqlEntity = gql_type_from_table(Entity)
GqlEntityType = gql_type_from_table(EntityType)
GqlRelType = gql_type_from_table(EntityRelationshipType)
```

This replaces 30+ hand-written type classes with a single derivation call
each. Custom resolvers (computed fields, nested lookups) can be added by
subclassing the generated type.

## 5. Resolver simplification

With auto-derived types, resolvers become trivial:

```python
@strawberry.field
def entities(self) -> list[GqlEntity]:
    return Entity.all()  # works if GqlEntity matches Entity's shape
```

## 6. Lit + Apollo: watchFragment controller

Apollo's `useFragment` is a React hook, but the underlying API is
`client.cache.watchFragment()` which is framework-agnostic. A reusable
Lit controller provides the same per-component fragment-level reactivity:

```typescript
import type { ReactiveControllerHost } from "lit";
import type { DocumentNode, StoreObject } from "@apollo/client";
import { getClient } from "shenas-frontends";

export class FragmentController<T> {
  host: ReactiveControllerHost;
  data: T | null = null;

  constructor(
    host: ReactiveControllerHost,
    fragment: DocumentNode,
    id: StoreObject,
  ) {
    this.host = host;
    host.addController(this);
    const client = getClient();
    client.cache.watchFragment({ fragment, from: id }, (result) => {
      this.data = result.data as T;
      host.requestUpdate();
    });
  }
}
```

Components subscribe to exactly the fields they declared in their fragment
and ignore changes to other fields on the same cache entry.

## 7. Optional: GraphQL codegen for frontend type safety

After the fragment convention is established, `graphql-codegen` can
generate TypeScript interfaces from the schema + query/fragment files,
eliminating the manual `interface Transform { ... }` declarations on the
frontend.

### Setup

1. Export schema:
   `strawberry export-schema app.graphql:schema > schema.graphql`
   (CI step, requires Python env)
2. Config: `codegen.yml` with `typescript` + `typescript-operations`
   plugins
3. Output: `src/graphql/__generated__/types.ts` (gitignored or committed)
4. Lit usage: import generated types for `@state()` declarations; no
   hooks needed (hooks plugins are React-only)

### Pros

- Type safety across the wire -- field typos in fragments caught at build
  time
- No manual TS interfaces -- generated from schema
- Schema drift detection in CI -- codegen fails if frontend uses removed
  fields

### Cons

- Build step complexity: Python env must be available before JS codegen
  runs
- Maintenance of codegen config as schema evolves
- At ~16 queries / ~40 mutations the contract surface is small enough to
  maintain manually

### Recommendation

Defer to Phase 5 or later. The fragment convention and cache
normalization deliver the biggest wins first. Add codegen when the query
count grows past 50 or when a second consumer (mobile, CLI) queries the
schema.

## 8. Migration path

Each phase is independently shippable.

| Phase | PR scope | Risk |
|---|---|---|
| 1 | Add `gql_type_from_table` helper + derive 5 entity types. Keep old types as aliases. | Low |
| 2 | Add fragment convention: extract `PluginCard` fragment, use in sidebar. Keep monolithic query as fallback. | Low |
| 3 | Configure `InMemoryCache` typePolicies. No query changes needed. | Low |
| 4 | Split `GET_APP_DATA` into Shell + Sidebar tiers. Remove monolithic query. | Medium |
| 5 | Extract remaining fragments per component. Migrate page queries to compose fragments. Optionally add graphql-codegen. | Medium |
| 6 | Delete hand-written types that are now derived. Update mutations to use derived input types. | Medium |

## 9. What we're not doing

- **No Relay.** We're using Apollo's fragment system, not switching
  frameworks. The convention is manual (no compiler), which is
  appropriate for the codebase size.
- **No subscriptions.** Real-time updates continue to use SSE
  (OpenTelemetry dispatcher), not GraphQL subscriptions.
- **No schema stitching.** Single schema, single server.

## 10. Open questions

- Should mutations also use derived input types, or keep hand-written
  `@strawberry.input` for explicit control over what's writable?
- Should `gql_type_from_table` generate a `Node` interface (Relay-style
  global IDs) for future pagination/connection support?
- How to handle View classes (read-only, no PK) in the derived type
  system?
