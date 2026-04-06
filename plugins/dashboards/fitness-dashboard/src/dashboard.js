import { LitElement, html, css } from "lit";
import { query, arrowToColumns, arrowDatesToUnix } from "./arrow-client.js";
import "./chart-panel.js";

export class ShenasDashboard extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _loading: { state: true },
    _error: { state: true },
    _hrv: { state: true },
    _sleep: { state: true },
    _vitals: { state: true },
    _body: { state: true },
  };

  static styles = css`
    :host {
      display: block;
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px;
      background: #f8f8f8;
      min-height: 100vh;
    }
    h1 {
      font-size: 20px;
      font-weight: 600;
      color: #222;
      margin: 0 0 4px 0;
    }
    .subtitle {
      font-size: 13px;
      color: #888;
      margin-bottom: 24px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 0;
    }
    .error {
      color: #c00;
      background: #fee;
      padding: 12px;
      border-radius: 6px;
      font-size: 13px;
    }
    .loading {
      color: #888;
      font-size: 13px;
      padding: 24px;
      text-align: center;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._loading = true;
    this._error = null;
    this._hrv = null;
    this._sleep = null;
    this._vitals = null;
    this._body = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll() {
    this._loading = true;
    this._error = null;
    try {
      const [hrv, sleep, vitals, body] = await Promise.all([
        query(this.apiBase, "SELECT date, rmssd FROM metrics.daily_hrv ORDER BY date"),
        query(this.apiBase, "SELECT date, total_hours, deep_min, rem_min, light_min, score FROM metrics.daily_sleep ORDER BY date"),
        query(this.apiBase, "SELECT date, resting_hr, steps, active_kcal FROM metrics.daily_vitals ORDER BY date"),
        query(this.apiBase, "SELECT date, weight_kg FROM metrics.daily_body WHERE weight_kg IS NOT NULL ORDER BY date"),
      ]);
      this._hrv = this._prepTimeSeries(hrv, ["rmssd"]);
      this._sleep = this._prepTimeSeries(sleep, ["total_hours", "deep_min", "rem_min", "light_min"]);
      this._vitals = this._prepTimeSeries(vitals, ["resting_hr", "steps", "active_kcal"]);
      this._body = this._prepTimeSeries(body, ["weight_kg"]);
    } catch (e) {
      this._error = e.message;
    }
    this._loading = false;
  }

  _prepTimeSeries(table, valueColumns) {
    const cols = arrowToColumns(table);
    if (!cols.date || cols.date.length === 0) return null;
    const timestamps = arrowDatesToUnix(cols.date);
    const series = [timestamps];
    for (const name of valueColumns) {
      if (cols[name]) {
        series.push(Float64Array.from(cols[name], (v) => (v == null ? null : Number(v))));
      }
    }
    return series;
  }

  render() {
    if (this._loading) return html`<div class="loading">Loading...</div>`;
    if (this._error) return html`<div class="error">${this._error}</div>`;

    return html`
      <div class="grid">
        <chart-panel
          title="HRV (RMSSD)"
          .data=${this._hrv}
          .series=${[{ label: "rmssd", color: "#6b5ce7" }]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" }, label: "ms" }]}
        ></chart-panel>

        <chart-panel
          title="Sleep"
          .data=${this._sleep}
          .series=${[
            { label: "total hrs", color: "#4a90d9" },
            { label: "deep min", color: "#2d5f8a" },
            { label: "rem min", color: "#7bb3e0" },
            { label: "light min", color: "#b8d4ed" },
          ]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" } }]}
        ></chart-panel>

        <chart-panel
          title="Resting Heart Rate"
          .data=${this._vitals ? [this._vitals[0], this._vitals[1]] : null}
          .series=${[{ label: "bpm", color: "#e74c3c" }]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" }, label: "bpm" }]}
        ></chart-panel>

        <chart-panel
          title="Steps"
          .data=${this._vitals ? [this._vitals[0], this._vitals[2]] : null}
          .series=${[{ label: "steps", color: "#27ae60", fill: "rgba(39,174,96,0.1)" }]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" } }]}
        ></chart-panel>

        <chart-panel
          title="Active Calories"
          .data=${this._vitals ? [this._vitals[0], this._vitals[3]] : null}
          .series=${[{ label: "kcal", color: "#e67e22", fill: "rgba(230,126,34,0.1)" }]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" } }]}
        ></chart-panel>

        <chart-panel
          title="Weight"
          .data=${this._body}
          .series=${[{ label: "kg", color: "#8e44ad" }]}
          .axes=${[{ stroke: "#888", grid: { stroke: "#f4f4f4" }, label: "kg" }]}
        ></chart-panel>
      </div>
    `;
  }
}

customElements.define("shenas-dashboard", ShenasDashboard);
