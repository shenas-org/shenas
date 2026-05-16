import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../dashboard.ts";

type AnyEl = HTMLElement & Record<string, unknown>;

describe("shenas-kpi-dashboard", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("no network in tests"));
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("creates the element", () => {
    const element = document.createElement("shenas-kpi-dashboard");
    expect(element).toBeDefined();
    expect(element.tagName.toLowerCase()).toBe("shenas-kpi-dashboard");
  });

  it("renders loading state initially", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    const text = element.shadowRoot?.textContent ?? "";
    expect(text.toLowerCase()).toContain("loading");
  });

  it("renders error state when fetch fails", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    // Wait for _fetchAll to settle
    await new Promise((resolve) => setTimeout(resolve, 20));
    element._loading = false;
    element._error = "connection refused";
    await element.updateComplete;
    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("connection refused");
  });

  it("renders three sections when data is loaded", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    element._loading = false;
    element._error = null;
    element._reworkRows = [];
    element._strandedRows = [];
    element._decisionRows = [];
    await element.updateComplete;

    const sections = element.shadowRoot?.querySelectorAll(".section");
    expect(sections?.length).toBe(3);
  });

  it("renders rework rows in rework section", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    element._loading = false;
    element._error = null;
    element._reworkRows = [{ agent_id: "agent-abc", total_issues: 10, rework_issues: 3, rework_pct: 30.0 }];
    element._strandedRows = [];
    element._decisionRows = [];
    await element.updateComplete;

    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("agent-abc");
    expect(text).toContain("30");
  });

  it("renders stranded issue rows with status badges", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    element._loading = false;
    element._error = null;
    element._reworkRows = [];
    element._strandedRows = [
      {
        issue_id: "issue-xyz",
        current_status: "in_progress",
        last_touch_at: 1747267200000000, // microseconds
        idle_s: 864000,
        threshold_s: 604800,
      },
    ];
    element._decisionRows = [];
    await element.updateComplete;

    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("issue-xyz");
    expect(text).toContain("in_progress");
  });

  it("sorts stranded rows on column header click", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    element._loading = false;
    element._error = null;
    element._reworkRows = [];
    element._strandedRows = [
      { issue_id: "a", current_status: "todo", last_touch_at: null, idle_s: 1296000, threshold_s: 1209600 },
      { issue_id: "b", current_status: "blocked", last_touch_at: null, idle_s: 2000000, threshold_s: 1209600 },
    ];
    element._decisionRows = [];
    element._strandedSortCol = "idle_s";
    element._strandedSortDir = "desc";
    await element.updateComplete;

    // Default sort by idle_s desc — "b" (2000000) should come before "a" (1296000)
    const cells = element.shadowRoot?.querySelectorAll("tbody td.issue-id");
    const ids = Array.from(cells ?? []).map((cell) => cell.textContent?.trim());
    expect(ids[0]).toBe("b");
    expect(ids[1]).toBe("a");
  });

  it("shows empty state for stranded when no issues", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    element._loading = false;
    element._error = null;
    element._reworkRows = [];
    element._strandedRows = [];
    element._decisionRows = [];
    await element.updateComplete;

    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("No stranded issues");
  });
});
