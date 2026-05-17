import { describe, expect, it } from "vitest";
import { createTestHarness } from "@paperclipai/plugin-sdk/testing";
import manifest from "../src/manifest.js";
import plugin from "../src/worker.js";

describe("spend-telemetry manifest", () => {
  it("declares required capabilities", () => {
    expect(manifest.capabilities).toContain("agents.read");
    expect(manifest.capabilities).toContain("issues.read");
    expect(manifest.capabilities).toContain("database.namespace.read");
    expect(manifest.capabilities).toContain("api.routes.register");
    expect(manifest.capabilities).toContain("ui.detailTab.register");
    expect(manifest.capabilities).toContain("ui.dashboardWidget.register");
  });

  it("whitelists cost_events, heartbeat_runs, agents, issues in coreReadTables", () => {
    const tables = manifest.database?.coreReadTables ?? [];
    expect(tables).toContain("cost_events");
    expect(tables).toContain("heartbeat_runs");
    expect(tables).toContain("agents");
    expect(tables).toContain("issues");
  });

  it("has no UI slots in scaffold phase", () => {
    expect(manifest.ui?.slots ?? []).toHaveLength(0);
  });
});

describe("spend-by-issue data handler", () => {
  it("returns error when companyId is missing", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const result = await harness.getData<{ error?: string }>("spend-by-issue", {});
    expect(result.error).toBe("companyId_required");
  });

  it("queries cost_events joined to issues with 30-day window", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const queriesBefore = harness.dbQueries.length;
    await harness.getData<{ rows: unknown[] }>("spend-by-issue", { companyId: "company-1" });

    const query = harness.dbQueries[queriesBefore];
    expect(query).toBeDefined();
    expect(query.sql).toContain("cost_events");
    expect(query.sql).toContain("issues");
    expect(query.sql).toContain("origin_kind");
    expect(query.sql).toContain("work_mode");
    expect(query.sql).toContain("30 days");
    expect(query.params).toContain("company-1");
    // Tenancy predicate must also be on the JOIN, not only in the WHERE clause.
    expect(query.sql).toMatch(/LEFT JOIN issues i ON i\.id = ce\.issue_id AND i\.company_id/);
  });

  it("SQL uses COUNT(DISTINCT heartbeat_run_id) for run deduplication", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    await harness.getData<{ rows: unknown[] }>("spend-by-issue", { companyId: "company-1" });
    const sql = harness.dbQueries[0].sql;

    // run_count must deduplicate by heartbeat_run_id so two cost_events from the
    // same run count as one run. The SQL has COUNT(*) for event_count (legitimate)
    // but must not use COUNT(*) for the run_count column alias.
    expect(sql).toContain("COUNT(DISTINCT ce.heartbeat_run_id)");
    expect(sql).not.toMatch(/COUNT\(\*\)\s+AS\s+run_count/i);
  });

  it("SQL counts subscription_included rows separately", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    await harness.getData<{ rows: unknown[] }>("spend-by-issue", { companyId: "company-1" });
    const sql = harness.dbQueries[0].sql;

    expect(sql).toContain("subscription_included");
    expect(sql).toContain("FILTER");
  });
});

describe("spend-detail data handler", () => {
  it("returns error when issueId or companyId is missing", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const result = await harness.getData<{ error?: string }>("spend-detail", {
      companyId: "company-1",
    });
    expect(result.error).toBe("issueId_and_companyId_required");
  });

  it("filters by issueId and companyId", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);

    const queriesBefore = harness.dbQueries.length;
    await harness.getData<{ rows: unknown[] }>("spend-detail", {
      issueId: "issue-abc",
      companyId: "company-1",
    });

    const query = harness.dbQueries[queriesBefore];
    expect(query.sql).toContain("cost_events");
    expect(query.sql).toContain("billing_type");
    expect(query.params).toContain("issue-abc");
    expect(query.params).toContain("company-1");
  });
});

describe("health check", () => {
  it("returns ok", async () => {
    const harness = createTestHarness({ manifest, capabilities: [...manifest.capabilities] });
    await plugin.definition.setup(harness.ctx);
    const health = await plugin.definition.onHealth!();
    expect(health.status).toBe("ok");
  });
});
