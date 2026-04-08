import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock uPlot -- the real uPlot requires a canvas context happy-dom does not provide
const { uplotCtor } = vi.hoisted(() => ({
  uplotCtor: vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
    setSize: vi.fn(),
  })),
}));
vi.mock("uplot", () => ({ default: uplotCtor }));
vi.mock("uplot/dist/uPlot.min.css?inline", () => ({ default: "" }));

import "../chart-panel.ts";

type AnyEl = HTMLElement & Record<string, any>;

describe("chart-panel", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    uplotCtor.mockReset();
    uplotCtor.mockImplementation(() => ({
      destroy: () => {},
      setSize: () => {},
    }));
  });

  afterEach(() => {
    document.querySelectorAll("chart-panel").forEach((p) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (p as any)._chart = null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (p as any)._ro = null;
    });
    document.body.innerHTML = "";
  });

  it("creates the element", () => {
    const el = document.createElement("chart-panel");
    expect(el).toBeDefined();
    expect(el.tagName.toLowerCase()).toBe("chart-panel");
  });

  it("renders a chart-wrap container and no-data message when empty", async () => {
    const el = document.createElement("chart-panel") as AnyEl;
    el.title = "Test";
    document.body.appendChild(el);
    await el.updateComplete;
    const wrap = el.shadowRoot?.querySelector(".chart-wrap");
    expect(wrap).toBeTruthy();
    const noData = el.shadowRoot?.querySelector(".no-data");
    expect(noData).toBeTruthy();
  });

  it("invokes uPlot constructor when data and series are provided", async () => {
    const el = document.createElement("chart-panel") as AnyEl;
    el.title = "HRV";
    el.series = [{ label: "rmssd", color: "#6b5ce7" }];
    el.axes = [{ stroke: "#888", grid: { stroke: "#f4f4f4" }, label: "ms" }];
    el.data = [[0, 86400, 172800], Float64Array.from([1, 2, 3])];
    document.body.appendChild(el);
    await el.updateComplete;
    await el.updateComplete;

    expect(uplotCtor).toHaveBeenCalled();
    const callArgs = uplotCtor.mock.calls[0];
    // opts is first arg
    expect(callArgs[0]).toMatchObject({ height: 200 });
    expect(Array.isArray(callArgs[0].series)).toBe(true);
    expect(Array.isArray(callArgs[0].axes)).toBe(true);
  });
});
