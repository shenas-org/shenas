import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock echarts -- the real echarts requires a canvas context happy-dom does not provide
const { initFn, setOptionFn, disposeFn: _disposeFn, resizeFn: _resizeFn } = vi.hoisted(() => {
  const setOption = vi.fn();
  const dispose = vi.fn();
  const resize = vi.fn();
  const init = vi.fn(() => ({ setOption, dispose, resize }));
  return { initFn: init, setOptionFn: setOption, disposeFn: dispose, resizeFn: resize };
});
vi.mock("echarts/core", () => ({
  init: initFn,
  use: vi.fn(),
}));
vi.mock("echarts/charts", () => ({ LineChart: {} }));
vi.mock("echarts/components", () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
  DataZoomComponent: {},
}));
vi.mock("echarts/renderers", () => ({ CanvasRenderer: {} }));

import "../chart-panel.ts";

type AnyEl = HTMLElement & Record<string, unknown>;

describe("chart-panel", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    initFn.mockClear();
    setOptionFn.mockClear();
  });

  afterEach(() => {
    document.querySelectorAll("chart-panel").forEach((p) => {
      (p as AnyEl)._chart = null;
      (p as AnyEl)._ro = null;
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
    await (el as { updateComplete: Promise<void> }).updateComplete;
    const wrap = (el as HTMLElement).shadowRoot?.querySelector(".chart-wrap");
    expect(wrap).toBeTruthy();
    const noData = (el as HTMLElement).shadowRoot?.querySelector(".no-data");
    expect(noData).toBeTruthy();
  });

  it("invokes echarts.init when data and series are provided", async () => {
    const el = document.createElement("chart-panel") as AnyEl;
    el.title = "HRV";
    el.series = [{ label: "rmssd", color: "#6b5ce7" }];
    el.axes = [{ stroke: "#888", grid: { stroke: "#f4f4f4" }, label: "ms" }];
    el.data = [[0, 86400, 172800], Float64Array.from([1, 2, 3])];
    document.body.appendChild(el);
    await (el as { updateComplete: Promise<void> }).updateComplete;
    await (el as { updateComplete: Promise<void> }).updateComplete;

    expect(initFn).toHaveBeenCalled();
    expect(setOptionFn).toHaveBeenCalled();
    const option = setOptionFn.mock.calls[0][0];
    expect(option.xAxis).toBeDefined();
    expect(option.series).toHaveLength(1);
    expect(option.series[0].name).toBe("rmssd");
  });
});
