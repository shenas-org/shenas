import { describe, expect, it } from "vitest";
import { createTestHarness } from "@paperclipai/plugin-sdk/testing";
import manifest from "../src/manifest.js";
import plugin from "../src/worker.js";

const MOCK_ACTOR = {
  actorType: "user" as const,
  actorId: "user-1",
  userId: "user-1",
};

describe("agent-token-monitor plugin", () => {
  it("setup registers token-totals and runs data handlers", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const totals = await harness.getData<{ rows: unknown[] }>("token-totals", {
      companyId: "company-1",
    });
    expect(totals.rows).toEqual([]);

    expect(harness.dbQueries.length).toBeGreaterThanOrEqual(1);
    const totalsSql = harness.dbQueries[0].sql;
    expect(totalsSql).toContain("cost_events");
    expect(totalsSql).toContain("input_tokens");
    expect(totalsSql).toContain("subscription_run_count");
    expect(harness.dbQueries[0].params).toContain("company-1");
  });

  it("runs data handler passes agentId filter when provided", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const runsBefore = harness.dbQueries.length;
    await harness.getData<{ rows: unknown[] }>("runs", {
      companyId: "company-1",
      agentId: "agent-99",
    });

    const runsQuery = harness.dbQueries[runsBefore];
    expect(runsQuery.sql).toContain("heartbeat_runs");
    expect(runsQuery.params).toContain("agent-99");
  });

  it("health check returns ok", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);
    const health = await plugin.definition.onHealth!();
    expect(health.status).toBe("ok");
  });

  it("run-count SQL uses COUNT(DISTINCT heartbeat_run_id), not COUNT(*)", async () => {
    // Verify the SQL emitted by the token-totals handler deduplicates by run,
    // not by individual cost_event rows. Two cost_events sharing one run must
    // count as 1 run. We can't execute real SQL in the test harness, so we
    // assert the shape of the query string that will be sent to the database.
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    await harness.getData<{ rows: unknown[] }>("token-totals", { companyId: "company-1" });

    const sql = harness.dbQueries[0].sql;
    // Must deduplicate by heartbeat_run_id, not COUNT(*) on cost_events rows
    expect(sql).toContain("COUNT(DISTINCT ce.heartbeat_run_id)");
    expect(sql).not.toMatch(/COUNT\(\*\)/);
  });

  it("onApiRequest returns 400 when companyId is missing from query", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const result = await plugin.definition.onApiRequest!({
      routeKey: "token-totals",
      method: "GET",
      path: "/token-totals",
      params: {},
      query: {},
      headers: {},
      body: null,
      actor: MOCK_ACTOR,
      companyId: "company-1",
    });

    expect(result.status).toBe(400);
    expect((result.body as { error: string }).error).toBe("companyId_required");
  });

  it("onApiRequest reads companyId from query, not params", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const queriesBefore = harness.dbQueries.length;
    const result = await plugin.definition.onApiRequest!({
      routeKey: "token-totals",
      method: "GET",
      path: "/token-totals",
      params: { companyId: "should-be-ignored" },
      query: { companyId: "company-from-query" },
      headers: {},
      body: null,
      actor: MOCK_ACTOR,
      companyId: "company-1",
    });

    expect(result.status).toBe(200);
    // The DB query must be scoped to the query-sourced companyId, not params
    const queryAfter = harness.dbQueries[queriesBefore];
    expect(queryAfter.params).toContain("company-from-query");
    expect(queryAfter.params).not.toContain("should-be-ignored");
  });
});
