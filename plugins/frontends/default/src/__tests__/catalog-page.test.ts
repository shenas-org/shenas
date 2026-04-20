import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../catalog-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

const SAMPLE_RESOURCES = [
  {
    id: "garmin.activities",
    schemaName: "garmin",
    tableName: "activities",
    displayName: "Activities",
    description: "Garmin Connect activities",
    plugin: { name: "garmin", displayName: "Garmin Connect" },
    kind: "event",
    queryHint: null,
    asOfMacro: null,
    primaryKey: ["id"],
    columns: [{ name: "id", dbType: "VARCHAR", nullable: false, description: "", unit: null }],
    timeColumns: { timeAt: "started_at", timeStart: null, timeEnd: null },
    freshness: { lastRefreshed: "2025-01-15T10:00:00", slaMinutes: 60, isStale: false },
    quality: { expectedRowCountMin: null, expectedRowCountMax: null, actualRowCount: 500, latestChecks: [] },
    userNotes: "",
    tags: [],
  },
  {
    id: "garmin.sleep",
    schemaName: "garmin",
    tableName: "sleep",
    displayName: "Sleep Sessions",
    description: "Sleep tracking data",
    plugin: { name: "garmin", displayName: "Garmin Connect" },
    kind: "interval",
    queryHint: null,
    asOfMacro: null,
    primaryKey: ["id"],
    columns: [],
    timeColumns: { timeAt: null, timeStart: "start_time", timeEnd: "end_time" },
    freshness: { lastRefreshed: null, slaMinutes: null, isStale: false },
    quality: { expectedRowCountMin: null, expectedRowCountMax: null, actualRowCount: null, latestChecks: [] },
    userNotes: "test note",
    tags: ["sleep"],
  },
  {
    id: "metrics.daily_hrv",
    schemaName: "metrics",
    tableName: "daily_hrv",
    displayName: "Daily HRV",
    description: "Heart rate variability metrics",
    plugin: { name: "fitness", displayName: "Fitness" },
    kind: "aggregate",
    queryHint: null,
    asOfMacro: null,
    primaryKey: ["date"],
    columns: [],
    timeColumns: { timeAt: "date", timeStart: null, timeEnd: null },
    freshness: { lastRefreshed: "2025-01-10T08:00:00", slaMinutes: 1440, isStale: true },
    quality: { expectedRowCountMin: 100, expectedRowCountMax: 10000, actualRowCount: 5000, latestChecks: [] },
    userNotes: "",
    tags: ["hrv", "fitness"],
  },
];

function mount(render = false): AnyEl {
  const el = document.createElement("shenas-catalog") as AnyEl;
  if (!render) {
    (el as unknown as { shouldUpdate: () => boolean }).shouldUpdate = () => false;
  }
  document.body.appendChild(el);
  return el;
}

describe("shenas-catalog", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ data: { dataResources: SAMPLE_RESOURCES } }),
    );
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-catalog");
    expect(el.tagName.toLowerCase()).toBe("shenas-catalog");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el._expanded).toBeNull();
    expect(el._detail).toBeNull();
    expect(el._message).toBeNull();
    expect(el._search).toBe("");
    expect(el._filterKind).toBe("");
  });

  // -- _formatRows -------------------------------------------------------

  it("formats null row count as --", () => {
    const el = mount();
    expect(el._formatRows(null)).toBe("--");
    expect(el._formatRows(undefined)).toBe("--");
  });

  it("formats millions", () => {
    const el = mount();
    expect(el._formatRows(1_500_000)).toBe("1.5M");
    expect(el._formatRows(2_000_000)).toBe("2.0M");
  });

  it("formats thousands", () => {
    const el = mount();
    expect(el._formatRows(1_500)).toBe("1.5k");
    expect(el._formatRows(999)).toBe("999");
  });

  it("formats small numbers as-is", () => {
    const el = mount();
    expect(el._formatRows(0)).toBe("0");
    expect(el._formatRows(42)).toBe("42");
  });

  // -- _filtered ---------------------------------------------------------
  // Inject mock resources directly via the private _resourcesQuery.data
  // to avoid Apollo cache timing issues between tests.

  function withResources(): AnyEl {
    const el = document.createElement("shenas-catalog") as AnyEl;
    // Prevent Lit rendering to avoid background render errors from missing DOM context
    (el as unknown as { shouldUpdate: () => boolean }).shouldUpdate = () => false;
    el._resourcesQuery = { data: { dataResources: SAMPLE_RESOURCES }, loading: false };
    return el;
  }

  it("returns all resources when no search or filter", () => {
    const el = withResources();
    el._search = "";
    el._filterKind = "";
    expect(el._filtered().length).toBe(3);
  });

  it("filters by search term against id", () => {
    const el = withResources();
    el._search = "garmin";
    const filtered = el._filtered();
    expect(filtered.length).toBe(2);
    expect(filtered.every((r: any) => r.id.includes("garmin"))).toBe(true);
  });

  it("filters by search term against displayName", () => {
    const el = withResources();
    el._search = "HRV";
    const filtered = el._filtered();
    expect(filtered.length).toBe(1);
    expect(filtered[0].displayName).toBe("Daily HRV");
  });

  it("filters by search term against description", () => {
    const el = withResources();
    el._search = "variability";
    expect(el._filtered().length).toBe(1);
  });

  it("filters by kind", () => {
    const el = withResources();
    el._filterKind = "event";
    const filtered = el._filtered();
    expect(filtered.length).toBe(1);
    expect(filtered[0].kind).toBe("event");
  });

  it("combines search and kind filter", () => {
    const el = withResources();
    el._search = "garmin";
    el._filterKind = "interval";
    const filtered = el._filtered();
    expect(filtered.length).toBe(1);
    expect(filtered[0].id).toBe("garmin.sleep");
  });

  it("returns empty array when nothing matches", () => {
    const el = withResources();
    el._search = "nonexistent";
    expect(el._filtered().length).toBe(0);
  });

  // -- _expand / collapse ------------------------------------------------

  it("toggles expansion off when expanding same id", async () => {
    const el = mount();
    el._expanded = "garmin.activities";
    await el._expand("garmin.activities");
    expect(el._expanded).toBeNull();
    expect(el._detail).toBeNull();
  });

  // -- _navigateToPlugin -------------------------------------------------

  it("dispatches navigate event for plugin link", () => {
    const el = mount();
    const handler = vi.fn();
    el.addEventListener("navigate", handler);
    el._navigateToPlugin("garmin", "source");
    expect(handler).toHaveBeenCalled();
    const detail = handler.mock.calls[0][0].detail;
    expect(detail.path).toBe("/settings/source/garmin");
    expect(detail.label).toBe("garmin");
  });
});
