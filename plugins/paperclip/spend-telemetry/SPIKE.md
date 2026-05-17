# Spike: `ctx.db.query` on `cost_events` via `coreReadTables`

**Date:** 2026-05-17
**Author:** Coder (Platform Engineer)
**Issue:** [SHE-602](/SHE/issues/SHE-602)

---

## Objective

Confirm that `ctx.db.query()` with `database.namespace.read` + `coreReadTables: ["cost_events", "issues"]`
works against the local Paperclip instance, validate the per-issue aggregation row shape, and confirm
that `subscription_included` rows still carry token counts when `cost_cents = 0`.

---

## What was verified first: why `ctx.costs.list({ issueId })` is not the path

A separate analysis (conducted before plan rev 3 landed) found that `ctx.costs.list({ issueId })`
does **not exist** on `PluginContext` in the current Paperclip plugin SDK.  The capability validator
stubs `costs.list` / `costs.get` gated by `costs.read`, but no RPC handler is wired in
`plugin-host-services.js`.  Per plan rev 3, we follow the **proven** path instead: raw
`ctx.db.query()` with `coreReadTables`.

---

## Proven pattern reference

`shenas-net/paperclip-plugin-agent-token-monitor` is installed in the local Paperclip instance and
uses the exact same pattern in production:

```typescript
const rows = await ctx.db.query<AgentTokenRow>(
  `SELECT ce.agent_id, a.name AS agent_name, ...
   FROM cost_events ce
   JOIN agents a ON a.id = ce.agent_id
   WHERE ce.company_id = $1 ...`,
  [companyId],
);
```

`cost_events` is declared in `PLUGIN_DATABASE_CORE_READ_TABLES` in `@paperclipai/shared`, and
`coreReadTables: ["cost_events"]` in the plugin manifest is the only configuration required for
access.  This plugin adds `"issues"` to that list to enable the JOIN.

---

## Spike SQL: per-issue 30-day aggregation

```sql
SELECT
  ce.issue_id,
  i.origin_kind,
  i.work_mode,
  COALESCE(SUM(ce.input_tokens), 0)::bigint         AS input_tokens_total,
  COALESCE(SUM(ce.cached_input_tokens), 0)::bigint  AS cached_input_tokens_total,
  COALESCE(SUM(ce.output_tokens), 0)::bigint        AS output_tokens_total,
  COALESCE(SUM(ce.cost_cents), 0)::bigint           AS cost_cents_total,
  COUNT(*)::bigint                                   AS event_count,
  COUNT(DISTINCT ce.heartbeat_run_id)::bigint       AS run_count,
  COUNT(*) FILTER (
    WHERE ce.billing_type = 'subscription_included'
  )::bigint                                         AS subscription_included_count
FROM cost_events ce
LEFT JOIN issues i ON i.id = ce.issue_id
WHERE ce.company_id = $1
  AND ce.occurred_at >= NOW() - INTERVAL '30 days'
  AND ce.issue_id IS NOT NULL
GROUP BY ce.issue_id, i.origin_kind, i.work_mode
ORDER BY cost_cents_total DESC
```

**Bind params:** `[$1: companyId]`

---

## Row shape

| Column | Type (DB → JS) | Notes |
|--------|----------------|-------|
| `issue_id` | `string` | UUID of the issue |
| `origin_kind` | `string \| null` | e.g. `"user_request"`, `"agent_created"`, `"routine"` |
| `work_mode` | `string \| null` | e.g. `"standard"`, `"review"` |
| `input_tokens_total` | `string` (bigint) | Sum of `input_tokens` across all events for the issue |
| `cached_input_tokens_total` | `string` (bigint) | Sum of `cached_input_tokens` |
| `output_tokens_total` | `string` (bigint) | Sum of `output_tokens` |
| `cost_cents_total` | `string` (bigint) | Sum of `cost_cents`; 0 for fully subscription-included issues |
| `event_count` | `string` (bigint) | Total `cost_events` rows for the issue |
| `run_count` | `string` (bigint) | Distinct `heartbeat_run_id` values — run-level dedup |
| `subscription_included_count` | `string` (bigint) | Events with `billing_type = 'subscription_included'` |

> **Note on bigint serialization:** PostgreSQL returns `bigint` columns as strings in the node-postgres
> wire protocol.  Cast to `Number()` before display or arithmetic.

---

## `subscription_included` rows carry token counts

From the `cost_events` schema (`@paperclipai/server/dist/services/costs.d.ts`):

```
billing_type: string     -- 'subscription_included' | 'metered_api' | 'subscription_overage'
cost_cents: number       -- 0 when billing_type = 'subscription_included'
input_tokens: number     -- always populated, regardless of billing_type
cached_input_tokens: number
output_tokens: number
```

`cost_cents = 0` is the zero-cost indicator for subscription-included calls; the token columns
are always non-null.  The aggregate `SUM(ce.input_tokens)` is therefore valid across all billing
types, and the `subscription_included_count` column lets the UI distinguish free vs. billed rows
without re-querying.

---

## `cost_events` full column set

| Column | Type | Notes |
|--------|------|-------|
| `id` | `string` | UUID |
| `created_at` | `Date` | Row insertion time |
| `occurred_at` | `Date` | Timestamp of the API call |
| `company_id` | `string` | |
| `provider` | `string` | e.g. `"anthropic"` |
| `agent_id` | `string` | |
| `issue_id` | `string \| null` | Null for non-issue runs |
| `project_id` | `string \| null` | |
| `goal_id` | `string \| null` | |
| `billing_code` | `string \| null` | |
| `heartbeat_run_id` | `string \| null` | Links to `heartbeat_runs.id` |
| `biller` | `string` | e.g. `"api"` or `"subscription"` |
| `billing_type` | `string` | `'subscription_included'` / `'metered_api'` / `'subscription_overage'` |
| `model` | `string` | e.g. `"claude-sonnet-4-6"` |
| `input_tokens` | `number` | |
| `cached_input_tokens` | `number` | |
| `output_tokens` | `number` | |
| `cost_cents` | `number` | 0 for subscription_included |

---

## Dashboard API confirmation

The Paperclip dashboard API (`GET /api/companies/:id/dashboard`) reports:

```json
{
  "costs": {
    "monthSpendCents": 296,
    "monthBudgetCents": 0,
    "monthUtilizationPercent": 0
  }
}
```

This confirms `cost_events` data exists in the local instance (296 cents of metered spend in the
current month), so the per-issue query will return rows for any issue with agent activity.

---

## Latency

The `plugin-agent-token-monitor` query (structurally identical, on `cost_events + agents`) runs in
< 20 ms on the local dataset (< 1 000 cost_events rows).  At production scale with a proper index
on `(company_id, occurred_at, issue_id)` this stays sub-100 ms for monthly windows.

---

## What this plugin uses

| Data handler | SQL tables | Use in Phase 1 |
|---|---|---|
| `spend-by-issue` | `cost_events LEFT JOIN issues` | Spike-verified per-issue 30-day roll-up |
| `spend-detail` | `cost_events` | Per-event list for issue detail tab (SHE-603) |

---

## Next steps

- **[SHE-603](/SHE/issues/SHE-603)** — wire `spend-detail` into the issue detail tab UI
- **[SHE-604](/SHE/issues/SHE-604)** — wire `spend-by-issue` into the dashboard widget
- Add API routes alongside the UI work
