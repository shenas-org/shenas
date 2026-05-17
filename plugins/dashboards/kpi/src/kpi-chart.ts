import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult, PropertyValues } from "lit";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

type ChartType = "line" | "bar-h";

export interface KpiSeries {
  name: string;
  values: number[];
  color?: string;
}

export class KpiChart extends LitElement {
  static properties = {
    title: { type: String },
    type: { type: String },
    labels: { type: Array },
    series: { type: Array },
    yLabel: { type: String, attribute: "y-label" },
  };

  declare title: string;
  declare type: ChartType;
  declare labels: string[];
  declare series: KpiSeries[];
  declare yLabel: string;

  static styles: CSSResult = css`
    :host {
      display: block;
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 16px;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    }
    .chart-wrap {
      width: 100%;
      height: 240px;
    }
    .no-data {
      color: #999;
      font-size: 13px;
      padding: 24px 0;
      text-align: center;
    }
  `;

  private _chart: echarts.ECharts | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  constructor() {
    super();
    this.title = "";
    this.type = "line";
    this.labels = [];
    this.series = [];
    this.yLabel = "";
  }

  updated(changed: PropertyValues): void {
    if (changed.has("labels") || changed.has("series") || changed.has("type")) {
      this._renderChart();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._chart) this._chart.dispose();
    if (this._resizeObserver) this._resizeObserver.disconnect();
  }

  private _renderChart(): void {
    const hasData = this.labels.length > 0 && this.series.some((s) => s.values.length > 0);
    if (!hasData) return;

    const wrap = this.renderRoot.querySelector(".chart-wrap") as HTMLElement | null;
    if (!wrap) return;

    if (this._chart) {
      this._chart.dispose();
      this._chart = null;
    }

    if (this.type === "bar-h") {
      const dynamicHeight = Math.max(240, this.labels.length * 40 + 60);
      wrap.style.height = `${dynamicHeight}px`;
    }

    this._chart = echarts.init(wrap);
    const option = this.type === "bar-h" ? this._barHOption() : this._lineOption();
    this._chart.setOption(option);

    if (!this._resizeObserver) {
      this._resizeObserver = new ResizeObserver(() => {
        if (this._chart) this._chart.resize();
      });
      this._resizeObserver.observe(wrap);
    }
  }

  private _barHOption(): echarts.EChartsCoreOption {
    const ecSeries = this.series.map((seriesItem) => ({
      name: seriesItem.name,
      type: "bar",
      data: seriesItem.values.map((value) => (value == null || isNaN(value) ? null : value)),
      itemStyle: { color: seriesItem.color ?? "#4a90d9" },
      barMaxWidth: 20,
    }));

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      legend: {
        show: this.series.length > 1,
        top: "bottom",
        textStyle: { fontSize: 11, color: "#888" },
        itemWidth: 12,
        itemHeight: 8,
      },
      grid: {
        left: 128,
        right: 24,
        top: 8,
        bottom: this.series.length > 1 ? 32 : 16,
        containLabel: false,
      },
      xAxis: {
        type: "value",
        name: this.yLabel,
        nameTextStyle: { fontSize: 10, color: "#888" },
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      yAxis: {
        type: "category",
        data: this.labels,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: {
          fontSize: 10,
          color: "#555",
          formatter: (labelValue: string) => {
            if (labelValue === "unassigned") return labelValue;
            return labelValue.length > 16 ? labelValue.slice(0, 8) + "…" : labelValue;
          },
        },
        axisTick: { show: false },
      },
      series: ecSeries,
    };
  }

  private _lineOption(): echarts.EChartsCoreOption {
    const ecSeries = this.series.map((seriesItem) => ({
      name: seriesItem.name,
      type: "line",
      data: seriesItem.values.map((value) => (value == null || isNaN(value) ? null : value)),
      smooth: true,
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { width: 2, color: seriesItem.color ?? "#4a90d9" },
      itemStyle: { color: seriesItem.color ?? "#4a90d9" },
    }));

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      legend: {
        show: this.series.length > 1,
        bottom: 0,
        textStyle: { fontSize: 11, color: "#888" },
        itemWidth: 12,
        itemHeight: 8,
      },
      grid: {
        left: 52,
        right: 16,
        top: 8,
        bottom: this.series.length > 1 ? 40 : 28,
        containLabel: false,
      },
      xAxis: {
        type: "category",
        data: this.labels,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888", rotate: 30 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        name: this.yLabel,
        nameTextStyle: { fontSize: 10, color: "#888" },
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      series: ecSeries,
    };
  }

  render(): TemplateResult {
    const hasData = this.labels.length > 0 && this.series.some((s) => s.values.length > 0);
    return html`
      <h3>${this.title}</h3>
      <div class="chart-wrap"></div>
      ${!hasData ? html`<div class="no-data">No data</div>` : ""}
    `;
  }
}

customElements.define("kpi-chart", KpiChart);
