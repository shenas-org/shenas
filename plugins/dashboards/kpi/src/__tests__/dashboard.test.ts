import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

vi.mock("shenas-frontends", () => ({
  query: vi.fn().mockRejectedValue(new Error("no network in tests")),
  arrowToRows: vi.fn().mockReturnValue([]),
  arrowToColumns: vi.fn().mockReturnValue({}),
  arrowDatesToUnix: vi.fn().mockReturnValue(new Float64Array()),
}));

const mockChart = {
  setOption: vi.fn(),
  dispose: vi.fn(),
  resize: vi.fn(),
};
vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: vi.fn(() => mockChart),
}));
vi.mock("echarts/charts", () => ({ BarChart: {}, LineChart: {} }));
vi.mock("echarts/components", () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
}));
vi.mock("echarts/renderers", () => ({ CanvasRenderer: {} }));

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../dashboard.ts";

type AnyEl = HTMLElement & Record<string, unknown> & { updateComplete: Promise<unknown> };

function setAllEmpty(element: AnyEl): void {
  element._loading = false;
  element._error = null;
  element._cycleTime = [];
  element._leadTimeTrend = [];
  element._wip = [];
  element._costPerIssue = [];
  element._weeklyCost = [];
  element._reworkRows = [];
  element._strandedRows = [];
  element._decisionRows = [];
}

describe("shenas-kpi-dashboard", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
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
    await new Promise((resolve) => setTimeout(resolve, 20));
    element._loading = false;
    element._error = "connection refused";
    await element.updateComplete;
    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("connection refused");
  });

  it("renders five kpi-chart elements when data is set", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    setAllEmpty(element);
    element._cycleTime = [{ agent_id: "agent-1", p50_hours: 2, p90_hours: 5, issue_count: 3 }];
    element._leadTimeTrend = [{ week: "2026-05-01", p50_lead_hours: 10 }];
    element._wip = [{ status: "in_progress", count: 4 }];
    element._costPerIssue = [{ agent_id: "agent-1", avg_cost_usd: 0.05, issue_count: 3 }];
    element._weeklyCost = [{ week: "2026-05-01", total_cost_usd: 0.15 }];

    await element.updateComplete;
    await element.updateComplete;

    const charts = element.shadowRoot?.querySelectorAll("kpi-chart");
    expect(charts && charts.length).toBe(5);
  });

  it("renders four quick-filter buttons", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    setAllEmpty(element);

    await element.updateComplete;
    await element.updateComplete;

    const buttons = element.shadowRoot?.querySelectorAll(".filter-btn");
    expect(buttons && buttons.length).toBe(4);
  });

  it("marks last_30d as active by default", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    setAllEmpty(element);

    await element.updateComplete;
    await element.updateComplete;

    const activeButton = element.shadowRoot?.querySelector(".filter-btn.active");
    expect(activeButton?.textContent?.trim()).toBe("Last 30d");
  });

  it("renders three phase-3 sections (rework, stranded, decision queue) when data is loaded", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    setAllEmpty(element);
    await element.updateComplete;
    await element.updateComplete;

    const sections = element.shadowRoot?.querySelectorAll(".section");
    expect(sections?.length).toBe(3);
  });

  it("renders rework rows in rework section", async () => {
    const element = document.createElement("shenas-kpi-dashboard") as AnyEl;
    document.body.appendChild(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 20));

    setAllEmpty(element);
    element._reworkRows = [{ agent_id: "agent-abc", total_issues: 10, rework_issues: 3, rework_pct: 30.0 }];
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

    setAllEmpty(element);
    element._strandedRows = [
      {
        issue_id: "issue-xyz",
        current_status: "in_progress",
        last_touch_at: 1747267200000000,
        idle_s: 864000,
        threshold_s: 604800,
      },
    ];
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

    setAllEmpty(element);
    element._strandedRows = [
      { issue_id: "a", current_status: "todo", last_touch_at: null, idle_s: 1296000, threshold_s: 1209600 },
      { issue_id: "b", current_status: "blocked", last_touch_at: null, idle_s: 2000000, threshold_s: 1209600 },
    ];
    element._strandedSortCol = "idle_s";
    element._strandedSortDir = "desc";
    await element.updateComplete;

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

    setAllEmpty(element);
    await element.updateComplete;

    const text = element.shadowRoot?.textContent ?? "";
    expect(text).toContain("No stranded issues");
  });
});
