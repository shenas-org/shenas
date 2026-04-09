import { LitElement, html, css, unsafeCSS } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import type { PropertyValues } from "lit";
import uPlot from "uplot";
import uPlotCSS from "uplot/dist/uPlot.min.css?inline";

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
    unsafeCSS(uPlotCSS),
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
        overflow: hidden;
      }
      .no-data {
        color: #999;
        font-size: 13px;
        padding: 24px 0;
        text-align: center;
      }
    `,
  ];

  private _chart: uPlot | null;
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
    if (this._chart) this._chart.destroy();
    if (this._ro) this._ro.disconnect();
  }

  _renderChart(): void {
    if (!this.data || this.data.length < 2 || this.data[0].length === 0) return;
    if (this._chart) {
      this._chart.destroy();
      this._chart = null;
    }

    const wrap = this.renderRoot.querySelector(".chart-wrap") as HTMLElement | null;
    if (!wrap) return;

    const width = wrap.clientWidth || 600;

    const opts: uPlot.Options = {
      width,
      height: 200,
      cursor: { show: true, drag: { x: true, y: false } },
      scales: { x: { time: true } },
      axes: [
        {
          stroke: "#888",
          grid: { stroke: "#eee" },
          values: (_u: uPlot, vals: number[]) =>
            vals.map((v) => {
              const d = new Date(v * 1000);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }),
        },
        ...(this.axes.length ? this.axes : [{ stroke: "#888", grid: { stroke: "#f4f4f4" } }]),
      ],
      series: [
        {},
        ...this.series.map((s) => ({
          stroke: s.color || "#4a90d9",
          width: 2,
          points: { show: false },
          ...s,
          label: s.label,
        })),
      ],
    };

    this._chart = new uPlot(opts, this.data as uPlot.AlignedData, wrap);

    if (!this._ro) {
      this._ro = new ResizeObserver(() => {
        if (this._chart) {
          const w = wrap.clientWidth;
          if (w > 0) this._chart.setSize({ width: w, height: 200 });
        }
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
