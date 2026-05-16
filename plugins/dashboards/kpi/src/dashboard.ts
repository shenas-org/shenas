import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { query, arrowToRows } from "shenas-frontends";
import type { RowData } from "shenas-frontends";

// SQL queries for the three Phase 3 KPI sections.
// Phase 2 (throughput + cost charts) will extend this component.

const SQL_REWORK_RATE = `
  SELECT
    agent_at_terminal AS agent_id,
    COUNT(*) AS total_issues,
    SUM(CASE WHEN was_rework THEN 1 ELSE 0 END) AS rework_issues,
    ROUND(
      100.0 * SUM(CASE WHEN was_rework THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
      1
    ) AS rework_pct
  FROM datasets.paperclip_kpi__dim_issue_terminal
  WHERE agent_at_terminal IS NOT NULL
  GROUP BY agent_at_terminal
  ORDER BY rework_pct DESC
`.trim();

const SQL_STRANDED = `
  SELECT issue_id, current_status, last_touch_at, idle_s, threshold_s
  FROM datasets.paperclip_kpi__dim_issue_stranded
  ORDER BY idle_s DESC
`.trim();

const SQL_DECISION_QUEUE = `
  SELECT
    decider_agent_id AS agent_id,
    COUNT(*) AS total_decisions,
    COUNT(*) FILTER (WHERE decided_at > NOW() - INTERVAL '30 days') AS decisions_last_30d,
    ROUND(AVG(time_to_decide_s), 0) AS avg_time_to_decide_s
  FROM datasets.paperclip_kpi__fact_decision_outcome
  WHERE decider_agent_id IS NOT NULL
  GROUP BY decider_agent_id
  ORDER BY decisions_last_30d DESC
`.trim();

type SortDir = "asc" | "desc";

function formatIdleTime(idle_s: unknown): string {
  if (idle_s == null) return "—";
  const seconds = Number(idle_s);
  if (seconds >= 86400) return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 60)}m`;
}

function formatTimestamp(value: unknown): string {
  if (value == null) return "—";
  const n = typeof value === "bigint" ? Number(value) : Number(value);
  if (!Number.isFinite(n)) return String(value);
  // DuckDB timestamps come as microseconds or milliseconds
  const ms = n > 1e12 ? n / 1000 : n > 1e9 ? n : n * 1000;
  return new Date(ms).toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

function sortRows(rows: RowData[], col: string, dir: SortDir): RowData[] {
  return [...rows].sort((rowA, rowB) => {
    const valueA = rowA[col];
    const valueB = rowB[col];
    if (valueA == null && valueB == null) return 0;
    if (valueA == null) return dir === "asc" ? 1 : -1;
    if (valueB == null) return dir === "asc" ? -1 : 1;
    const numA = Number(valueA);
    const numB = Number(valueB);
    if (!Number.isNaN(numA) && !Number.isNaN(numB)) {
      return dir === "asc" ? numA - numB : numB - numA;
    }
    const strA = String(valueA);
    const strB = String(valueB);
    return dir === "asc" ? strA.localeCompare(strB) : strB.localeCompare(strA);
  });
}

export class ShenasKpiDashboard extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _loading: { state: true },
    _error: { state: true },
    _reworkRows: { state: true },
    _strandedRows: { state: true },
    _decisionRows: { state: true },
    _strandedSortCol: { state: true },
    _strandedSortDir: { state: true },
  };

  declare apiBase: string;
  declare _loading: boolean;
  declare _error: string | null;
  declare _reworkRows: RowData[] | null;
  declare _strandedRows: RowData[] | null;
  declare _decisionRows: RowData[] | null;
  declare _strandedSortCol: string;
  declare _strandedSortDir: SortDir;

  static styles: CSSResult = css`
    :host {
      display: block;
      font-family:
        system-ui,
        -apple-system,
        sans-serif;
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px;
      background: #f8f8f8;
      min-height: 100vh;
      color: #222;
    }
    h1 {
      font-size: 20px;
      font-weight: 600;
      margin: 0 0 4px 0;
    }
    .subtitle {
      font-size: 13px;
      color: #888;
      margin-bottom: 24px;
    }
    .section {
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
      margin-bottom: 20px;
      overflow: hidden;
    }
    .section-header {
      padding: 16px 20px 12px;
      border-bottom: 1px solid #f0f0f0;
    }
    .section-title {
      font-size: 15px;
      font-weight: 600;
      margin: 0 0 2px 0;
    }
    .section-desc {
      font-size: 12px;
      color: #888;
      margin: 0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th {
      text-align: left;
      padding: 10px 20px;
      background: #fafafa;
      font-weight: 600;
      font-size: 12px;
      color: #555;
      border-bottom: 1px solid #f0f0f0;
      white-space: nowrap;
    }
    th.sortable {
      cursor: pointer;
      user-select: none;
    }
    th.sortable:hover {
      background: #f0f0f0;
    }
    th .sort-indicator {
      margin-left: 4px;
      opacity: 0.5;
    }
    th.sort-active .sort-indicator {
      opacity: 1;
    }
    td {
      padding: 9px 20px;
      border-bottom: 1px solid #f9f9f9;
      vertical-align: middle;
    }
    tr:last-child td {
      border-bottom: none;
    }
    tr:hover td {
      background: #fafafa;
    }
    .pct-cell {
      font-weight: 600;
    }
    .pct-high {
      color: #c00;
    }
    .pct-mid {
      color: #e67e22;
    }
    .pct-low {
      color: #27ae60;
    }
    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }
    .status-in_progress {
      background: #fff3cd;
      color: #856404;
    }
    .status-todo {
      background: #e8f4fd;
      color: #0c5fa1;
    }
    .status-blocked {
      background: #fde8e8;
      color: #9c1515;
    }
    .empty {
      padding: 32px 20px;
      text-align: center;
      color: #aaa;
      font-size: 13px;
    }
    .error {
      color: #c00;
      background: #fee;
      padding: 12px 20px;
      font-size: 13px;
    }
    .loading {
      color: #888;
      font-size: 13px;
      padding: 32px;
      text-align: center;
    }
    .agent-id {
      font-family: monospace;
      font-size: 11px;
      color: #666;
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .issue-id {
      font-family: monospace;
      font-size: 11px;
      color: #666;
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._loading = true;
    this._error = null;
    this._reworkRows = null;
    this._strandedRows = null;
    this._decisionRows = null;
    this._strandedSortCol = "idle_s";
    this._strandedSortDir = "desc";
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll(): Promise<void> {
    this._loading = true;
    this._error = null;
    try {
      const [reworkTable, strandedTable, decisionTable] = await Promise.all([
        query(this.apiBase, SQL_REWORK_RATE),
        query(this.apiBase, SQL_STRANDED),
        query(this.apiBase, SQL_DECISION_QUEUE),
      ]);
      this._reworkRows = arrowToRows(reworkTable);
      this._strandedRows = arrowToRows(strandedTable);
      this._decisionRows = arrowToRows(decisionTable);
    } catch (error) {
      this._error = (error as Error).message;
    }
    this._loading = false;
  }

  _onStrandedSort(col: string): void {
    if (this._strandedSortCol === col) {
      this._strandedSortDir = this._strandedSortDir === "asc" ? "desc" : "asc";
    } else {
      this._strandedSortCol = col;
      this._strandedSortDir = col === "idle_s" ? "desc" : "asc";
    }
  }

  _sortIndicator(col: string): string {
    if (this._strandedSortCol !== col) return "↕";
    return this._strandedSortDir === "asc" ? "↑" : "↓";
  }

  _reworkPctClass(pct: unknown): string {
    const value = Number(pct);
    if (value >= 30) return "pct-high";
    if (value >= 10) return "pct-mid";
    return "pct-low";
  }

  _renderReworkSection(): TemplateResult {
    const rows = this._reworkRows;
    return html`
      <div class="section">
        <div class="section-header">
          <p class="section-title">Rework Rate per Agent</p>
          <p class="section-desc">Issues with an in_review → in_progress transition, grouped by terminal assignee</p>
        </div>
        ${rows === null
          ? html`<div class="loading">Loading...</div>`
          : rows.length === 0
            ? html`<div class="empty">No terminal issues found</div>`
            : html`
                <table>
                  <thead>
                    <tr>
                      <th>Agent</th>
                      <th>Total Issues</th>
                      <th>Rework Issues</th>
                      <th>Rework %</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${rows.map(
                      (row) => html`
                        <tr>
                          <td class="agent-id">${row.agent_id ?? "—"}</td>
                          <td>${row.total_issues ?? "—"}</td>
                          <td>${row.rework_issues ?? "—"}</td>
                          <td class=${`pct-cell ${this._reworkPctClass(row.rework_pct)}`}>
                            ${row.rework_pct != null ? `${row.rework_pct}%` : "—"}
                          </td>
                        </tr>
                      `,
                    )}
                  </tbody>
                </table>
              `}
      </div>
    `;
  }

  _renderStrandedSection(): TemplateResult {
    const allRows = this._strandedRows;
    const rows = allRows !== null ? sortRows(allRows, this._strandedSortCol, this._strandedSortDir) : null;

    const sortableTh = (col: string, label: string): TemplateResult => html`
      <th
        class=${`sortable${this._strandedSortCol === col ? " sort-active" : ""}`}
        @click=${() => this._onStrandedSort(col)}
      >
        ${label}<span class="sort-indicator">${this._sortIndicator(col)}</span>
      </th>
    `;

    return html`
      <div class="section">
        <div class="section-header">
          <p class="section-title">Stranded Issues</p>
          <p class="section-desc">
            Active issues (todo/in_progress/blocked) with no activity for ≥ 7d (in_progress) or ≥ 14d (todo/blocked)
          </p>
        </div>
        ${rows === null
          ? html`<div class="loading">Loading...</div>`
          : rows.length === 0
            ? html`<div class="empty">No stranded issues — all active work is being touched regularly</div>`
            : html`
                <table>
                  <thead>
                    <tr>
                      <th>Issue ID</th>
                      <th>Status</th>
                      ${sortableTh("last_touch_at", "Last Touch")} ${sortableTh("idle_s", "Idle Time")}
                      ${sortableTh("threshold_s", "Threshold")}
                    </tr>
                  </thead>
                  <tbody>
                    ${rows.map(
                      (row) => html`
                        <tr>
                          <td class="issue-id">${row.issue_id ?? "—"}</td>
                          <td>
                            <span
                              class=${`status-badge${row.current_status != null ? ` status-${row.current_status}` : ""}`}
                            >
                              ${row.current_status ?? "—"}
                            </span>
                          </td>
                          <td>${formatTimestamp(row.last_touch_at)}</td>
                          <td>${formatIdleTime(row.idle_s)}</td>
                          <td>
                            ${row.threshold_s === 604800
                              ? "7d"
                              : row.threshold_s === 1209600
                                ? "14d"
                                : row.threshold_s != null
                                  ? `${Math.floor(Number(row.threshold_s) / 86400)}d`
                                  : "—"}
                          </td>
                        </tr>
                      `,
                    )}
                  </tbody>
                </table>
              `}
      </div>
    `;
  }

  _renderDecisionQueueSection(): TemplateResult {
    const rows = this._decisionRows;
    return html`
      <div class="section">
        <div class="section-header">
          <p class="section-title">Decision Queue per Approver</p>
          <p class="section-desc">Approval and thread-interaction decisions made, with average response time</p>
        </div>
        ${rows === null
          ? html`<div class="loading">Loading...</div>`
          : rows.length === 0
            ? html`<div class="empty">No decision events found</div>`
            : html`
                <table>
                  <thead>
                    <tr>
                      <th>Approver</th>
                      <th>Total Decisions</th>
                      <th>Last 30d</th>
                      <th>Avg Response Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${rows.map(
                      (row) => html`
                        <tr>
                          <td class="agent-id">${row.agent_id ?? "—"}</td>
                          <td>${row.total_decisions ?? "—"}</td>
                          <td>${row.decisions_last_30d ?? "—"}</td>
                          <td>${row.avg_time_to_decide_s != null ? formatIdleTime(row.avg_time_to_decide_s) : "—"}</td>
                        </tr>
                      `,
                    )}
                  </tbody>
                </table>
              `}
      </div>
    `;
  }

  render(): TemplateResult {
    if (this._loading) return html`<div class="loading">Loading KPI data...</div>`;
    if (this._error) return html`<div class="error">${this._error}</div>`;

    return html`
      <h1>KPI Dashboard</h1>
      <p class="subtitle">Agent and company performance — rework, stranded work, and decision throughput</p>
      ${this._renderReworkSection()} ${this._renderStrandedSection()} ${this._renderDecisionQueueSection()}
    `;
  }
}

customElements.define("shenas-kpi-dashboard", ShenasKpiDashboard);
