import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult, PropertyValues } from "lit";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer]);

interface BarSeriesConfig {
  name: string;
  data: number[];
  color?: string;
}

interface LineSeriesConfig {
  label: string;
  color?: string;
  dashed?: boolean;
  yAxisIndex?: number;
}

interface AxisConfig {
  label?: string;
  stroke?: string;
}

export class ChartPanel extends LitElement {
  static properties = {
    title: { type: String },
    type: { type: String },
    categories: { type: Array },
    barSeries: { type: Array },
    data: { type: Array },
    series: { type: Array },
    axes: { type: Array },
  };

  declare title: string;
  declare type: "bar" | "line-dual";
  declare categories: string[];
  declare barSeries: BarSeriesConfig[];
  declare data: (Float64Array | number[])[] | null;
  declare series: LineSeriesConfig[];
  declare axes: AxisConfig[];

  static styles: CSSResult = css`
    :host {
      display: block;
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 16px;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    }
    .chart-wrap {
      width: 100%;
      height: 260px;
    }
    .no-data {
      color: #999;
      font-size: 13px;
      padding: 24px 0;
      text-align: center;
    }
  `;

  private _chart: echarts.ECharts | null = null;
  private _ro: ResizeObserver | null = null;

  constructor() {
    super();
    this.title = "";
    this.type = "bar";
    this.categories = [];
    this.barSeries = [];
    this.data = null;
    this.series = [];
    this.axes = [];
  }

  updated(changed: PropertyValues): void {
    if (changed.has("data") || changed.has("barSeries") || changed.has("categories") || changed.has("series")) {
      this._renderChart();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._chart) this._chart.dispose();
    if (this._ro) this._ro.disconnect();
  }

  _renderChart(): void {
    const wrap = this.renderRoot.querySelector(".chart-wrap") as HTMLElement | null;
    if (!wrap) return;

    if (this._chart) {
      this._chart.dispose();
      this._chart = null;
    }

    if (this.type === "bar") {
      this._renderBar(wrap);
    } else {
      this._renderLineDual(wrap);
    }

    if (this._chart && !this._ro) {
      this._ro = new ResizeObserver(() => {
        if (this._chart) this._chart.resize();
      });
      this._ro.observe(wrap);
    }
  }

  _renderBar(wrap: HTMLElement): void {
    if (!this.categories.length || !this.barSeries.length) return;

    this._chart = echarts.init(wrap);

    const ecSeries = this.barSeries.map((s) => ({
      name: s.name,
      type: "bar",
      data: s.data,
      itemStyle: { color: s.color ?? "#4a90d9" },
    }));

    this._chart.setOption({
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      legend: { bottom: 0, textStyle: { fontSize: 11, color: "#888" } },
      grid: { left: 50, right: 16, top: 8, bottom: 48, containLabel: false },
      xAxis: {
        type: "category",
        data: this.categories,
        axisLabel: { fontSize: 10, color: "#888", rotate: 20, overflow: "truncate", width: 80 },
        axisLine: { lineStyle: { color: "#ddd" } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        name: this.axes[0]?.label ?? "",
        nameTextStyle: { fontSize: 10, color: "#888" },
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      series: ecSeries,
    });
  }

  _renderLineDual(wrap: HTMLElement): void {
    if (!this.data || this.data.length < 2 || (this.data[0] as ArrayLike<unknown>).length === 0) return;

    this._chart = echarts.init(wrap);

    const timestamps = Array.from(this.data[0]);
    const xData = timestamps.map((ts) => {
      const d = new Date((ts as number) * 1000);
      return `${d.getFullYear()}-W${String(Math.ceil((d.getDate() + 6 - d.getDay()) / 7)).padStart(2, "0")}`;
    });

    const ecSeries = this.series.map((s, i) => ({
      name: s.label,
      type: "line",
      yAxisIndex: s.yAxisIndex ?? 0,
      data: Array.from(this.data![i + 1] ?? []).map((v) => (v == null || isNaN(v as number) ? null : v)),
      smooth: true,
      symbol: "none",
      lineStyle: { width: 2, color: s.color, type: s.dashed ? "dashed" : "solid" },
      itemStyle: { color: s.color },
    }));

    const leftAxis = this.axes[0];
    const rightAxis = this.axes[1];

    this._chart.setOption({
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      legend: { bottom: 0, textStyle: { fontSize: 11, color: "#888" } },
      grid: { left: 50, right: 50, top: 8, bottom: 48, containLabel: false },
      xAxis: {
        type: "category",
        data: xData,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888" },
        axisTick: { show: false },
      },
      yAxis: [
        {
          type: "value",
          name: leftAxis?.label ?? "",
          nameTextStyle: { fontSize: 10, color: "#888" },
          axisLine: { show: false },
          axisLabel: { fontSize: 10, color: "#888" },
          splitLine: { lineStyle: { color: "#f0f0f0" } },
        },
        {
          type: "value",
          name: rightAxis?.label ?? "",
          nameTextStyle: { fontSize: 10, color: rightAxis?.stroke ?? "#e67e22" },
          axisLine: { show: false },
          axisLabel: { fontSize: 10, color: rightAxis?.stroke ?? "#e67e22" },
          splitLine: { show: false },
        },
      ],
      dataZoom: [{ type: "inside", start: 0, end: 100 }],
      series: ecSeries,
    });
  }

  render(): TemplateResult {
    const hasBarData = this.type === "bar" && this.categories.length > 0 && this.barSeries.length > 0;
    const hasLineData =
      this.type === "line-dual" &&
      this.data !== null &&
      this.data.length >= 2 &&
      (this.data[0] as ArrayLike<unknown>).length > 0;
    const hasData = hasBarData || hasLineData;

    return html`
      <h3>${this.title}</h3>
      <div class="chart-wrap"></div>
      ${!hasData ? html`<div class="no-data">No data</div>` : ""}
    `;
  }
}

customElements.define("chart-panel", ChartPanel);
