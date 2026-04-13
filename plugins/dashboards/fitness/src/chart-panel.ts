import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import type { PropertyValues } from "lit";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer]);

interface SeriesConfig {
  label: string;
  color?: string;
  fill?: string;
  [key: string]: unknown;
}

interface AxisConfig {
  stroke?: string;
  grid?: { stroke: string };
  label?: string;
  [key: string]: unknown;
}

export class ChartPanel extends LitElement {
  static properties = {
    title: { type: String },
    data: { type: Array },
    series: { type: Array },
    axes: { type: Array },
  };

  declare title: string;
  declare data: (Float64Array | number[])[] | null;
  declare series: SeriesConfig[];
  declare axes: AxisConfig[];

  static styles: CSSResult[] = [
    css`
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
        height: 220px;
      }
      .no-data {
        color: #999;
        font-size: 13px;
        padding: 24px 0;
        text-align: center;
      }
    `,
  ];

  private _chart: echarts.ECharts | null;
  private _ro: ResizeObserver | null;

  constructor() {
    super();
    this.title = "";
    this.data = null;
    this.series = [];
    this.axes = [];
    this._chart = null;
    this._ro = null;
  }

  updated(changed: PropertyValues): void {
    if (changed.has("data") || changed.has("series")) {
      this._renderChart();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._chart) this._chart.dispose();
    if (this._ro) this._ro.disconnect();
  }

  _renderChart(): void {
    if (!this.data || this.data.length < 2 || this.data[0].length === 0) return;

    const wrap = this.renderRoot.querySelector(".chart-wrap") as HTMLElement | null;
    if (!wrap) return;

    if (this._chart) {
      this._chart.dispose();
      this._chart = null;
    }

    this._chart = echarts.init(wrap);

    // Convert unix timestamps to date strings for the x-axis
    const timestamps = Array.from(this.data[0]);
    const xData = timestamps.map((t) => {
      const d = new Date(t * 1000);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    });

    const axisLabel = this.axes[0]?.label || "";

    const ecSeries: echarts.EChartsCoreOption[] = this.series.map((s, i) => {
      const values = Array.from(this.data![i + 1] || []);
      return {
        name: s.label,
        type: "line",
        data: values.map((v) => (v == null || isNaN(v as number) ? null : v)),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: s.color || "#4a90d9" },
        itemStyle: { color: s.color || "#4a90d9" },
        areaStyle: s.fill ? { color: s.fill } : undefined,
      };
    });

    const option: echarts.EChartsCoreOption = {
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
        left: 45,
        right: 16,
        top: 8,
        bottom: this.series.length > 1 ? 40 : 24,
        containLabel: false,
      },
      xAxis: {
        type: "category",
        data: xData,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888" },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        name: axisLabel,
        nameTextStyle: { fontSize: 10, color: "#888" },
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      dataZoom: [
        {
          type: "inside",
          start: 0,
          end: 100,
        },
      ],
      series: ecSeries,
    };

    this._chart.setOption(option);

    if (!this._ro) {
      this._ro = new ResizeObserver(() => {
        if (this._chart) this._chart.resize();
      });
      this._ro.observe(wrap);
    }
  }

  render(): TemplateResult {
    const hasData = this.data && this.data.length >= 2 && this.data[0].length > 0;
    return html`
      <h3>${this.title}</h3>
      <div class="chart-wrap"></div>
      ${!hasData ? html`<div class="no-data">No data</div>` : ""}
    `;
  }
}

customElements.define("chart-panel", ChartPanel);
