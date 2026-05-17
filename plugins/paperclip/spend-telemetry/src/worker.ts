import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";

export type IssueCostRow = {
  issue_id: string;
  origin_kind: string | null;
  work_mode: string | null;
  input_tokens_total: string;
  cached_input_tokens_total: string;
  output_tokens_total: string;
  cost_cents_total: string;
  event_count: string;
  run_count: string;
  subscription_included_count: string;
};

export type SpendEventRow = {
  id: string;
  occurred_at: string;
  provider: string;
  model: string;
  agent_id: string;
  heartbeat_run_id: string | null;
  billing_code: string | null;
  billing_type: string;
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  cost_cents: number;
};

const plugin = definePlugin({
  async setup(ctx) {
    // Aggregated per-issue spend over the last 30 days, joined to issues for
    // origin_kind and work_mode context. Confirms subscription_included rows
    // carry full token counts even when cost_cents = 0.
    ctx.data.register("spend-by-issue", async (params) => {
      const { companyId } = params as { companyId: string };
      if (!companyId) return { error: "companyId_required" };

      const rows = await ctx.db.query<IssueCostRow>(
        `SELECT
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
         LEFT JOIN issues i ON i.id = ce.issue_id AND i.company_id = $1
         WHERE ce.company_id = $1
           AND ce.occurred_at >= NOW() - INTERVAL '30 days'
           AND ce.issue_id IS NOT NULL
         GROUP BY ce.issue_id, i.origin_kind, i.work_mode
         ORDER BY cost_cents_total DESC`,
        [companyId],
      );

      return { rows };
    });

    // Per-event breakdown for a single issue. Used by the detail tab (SHE-603).
    ctx.data.register("spend-detail", async (params) => {
      const { issueId, companyId } = params as {
        issueId: string;
        companyId: string;
      };
      if (!issueId || !companyId) return { error: "issueId_and_companyId_required" };

      const rows = await ctx.db.query<SpendEventRow>(
        `SELECT
           ce.id,
           ce.occurred_at,
           ce.provider,
           ce.model,
           ce.agent_id,
           ce.heartbeat_run_id,
           ce.billing_code,
           ce.billing_type,
           ce.input_tokens,
           ce.cached_input_tokens,
           ce.output_tokens,
           ce.cost_cents
         FROM cost_events ce
         WHERE ce.issue_id = $1
           AND ce.company_id = $2
         ORDER BY ce.occurred_at DESC
         LIMIT 200`,
        [issueId, companyId],
      );

      return { rows };
    });
  },

  async onHealth() {
    return { status: "ok", message: "spend-telemetry worker running" };
  },
});

export default plugin;
runWorker(plugin, import.meta.url);
