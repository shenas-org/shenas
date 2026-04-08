import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock uPlot and its CSS import -- happy-dom cannot render canvas-based charts
const { uplotCtor } = vi.hoisted(() => ({
  uplotCtor: vi.fn().mockImplementation(function (this: any) {
    this.destroy = () => {};
    this.setSize = () => {};
  }),
}));
vi.mock("uplot", () => ({ default: uplotCtor }));
vi.mock("uplot/dist/uPlot.min.css?inline", () => ({ default: "" }));

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../dashboard.ts";

type AnyEl = HTMLElement & Record<string, any>;

describe("shenas-dashboard", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("no network in tests"),
    );
  });

  afterEach(() => {
    // Proactively clear any _chart refs on lingering chart-panels to avoid
    // happy-dom teardown touching a stale uPlot mock.
    document.querySelectorAll("shenas-dashboard").forEach((d) => {
      d.shadowRoot?.querySelectorAll("chart-panel").forEach((p) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (p as any)._chart = null;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (p as any)._ro = null;
      });
    });
    document.body.innerHTML = "";
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-dashboard");
    expect(el).toBeDefined();
    expect(el.tagName.toLowerCase()).toBe("shenas-dashboard");
  });

  it("renders loading state initially", async () => {
    const el = document.createElement("shenas-dashboard") as AnyEl;
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text.toLowerCase()).toContain("loading");
  });

  it("renders chart-panel elements when timeseries are set", async () => {
    const el = document.createElement("shenas-dashboard") as AnyEl;
    document.body.appendChild(el);
    await el.updateComplete;
    // Wait for the async _fetchAll (which rejects due to mocked fetch) to settle
    await new Promise((r) => setTimeout(r, 20));

    el._loading = false;
    el._error = null;
    // Use empty data so chart-panel's _renderChart short-circuits and never
    // constructs a real uPlot instance (canvas is not available in happy-dom).
    const empty: number[] = [];
    const emptyVals = Float64Array.from([]);
    el._hrv = [empty, emptyVals];
    el._sleep = [empty, emptyVals, emptyVals, emptyVals, emptyVals];
    el._vitals = [empty, emptyVals, emptyVals, emptyVals];
    el._body = [empty, emptyVals];
    await el.updateComplete;
    await el.updateComplete;

    const panels = el.shadowRoot?.querySelectorAll("chart-panel");
    expect(panels && panels.length).toBeGreaterThan(0);
  });
});
