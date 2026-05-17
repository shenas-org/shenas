import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { query, arrowToRows } from "shenas-frontends";
import type { Table, RowData } from "shenas-frontends";
import "./kpi-chart.ts";
import type { KpiSeries } from "./kpi-chart.ts";

type QuickFilter = "last_7d" | "last_30d" | "last_90d" | "all_time";

interface CycleTimeRow extends RowData {
  agent_id: string;
  p50_hours: number;
  p90_hours: number;
  issue_count: number;
}

interface LeadTimeTrendRow extends RowData {
  week: string;
  p50_lead_hours: number;
}

interface WipRow extends RowData {
  status: string;
  count: number;
}

interface CostPerIssueRow extends RowData {
  agent_id: string;
  avg_cost_usd: number;
  issue_count: number;
}

interface WeeklyCostRow extends RowData {
  week: string;
  total_cost_usd: number;
}

const QUICK_FILTERS: { key: QuickFilter; label: string }[] = [
  { key: "last_7d", label: "Last 7d" },
  { key: "last_30d", label: "Last 30d" },
  { key: "last_90d", label: "Last 90d" },
  { key: "all_time", label: "All time" },
];

function timeFilter(column: string, filter: QuickFilter): string {
  if (filter === "all_time") return "1=1";
  const days = { last_7d: "7", last_30d: "30", last_90d: "90" }[filter];
  return `${column}::TIMESTAMP >= now() - INTERVAL ${days} DAY`;
}

function agentLabel(agentId: string, nameMap: Map<string, string>): string {
  if (agentId === "unassigned") return "unassigned";
  return nameMap.get(agentId) ?? agentId.slice(0, 8) + "…";
}

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
    _filter: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _cycleTime: { state: true },
    _leadTimeTrend: { state: true },
    _wip: { state: true },
    _costPerIssue: { state: true },
    _weeklyCost: { state: true },
    _reworkRows: { state: true },
    _strandedRows: { state: true },
    _decisionRows: { state: true },
    _strandedSortCol: { state: true },
    _strandedSortDir: { state: true },
  };

  declare apiBase: string;
  declare _filter: QuickFilter;
  declare _loading: boolean;
  declare _error: string | null;
  declare _cycleTime: CycleTimeRow[] | null;
  declare _leadTimeTrend: LeadTimeTrendRow[] | null;
  declare _wip: WipRow[] | null;
  declare _costPerIssue: CostPerIssueRow[] | null;
  declare _weeklyCost: WeeklyCostRow[] | null;
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
      max-width: 1080px;
      margin: 0 auto;
      padding: 24px 16px;
      background: #f8f8f8;
      min-height: 100vh;
      color: #222;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
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
    .filters {
      display: flex;
      gap: 6px;
    }
    .filter-btn {
      padding: 4px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      font-size: 12px;
      cursor: pointer;
      color: #555;
      line-height: 1.6;
    }
    .filter-btn:hover {
      border-color: #aaa;
    }
    .filter-btn.active {
      background: #222;
      color: #fff;
      border-color: #222;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 20px;
    }
    .full-width {
      grid-column: 1 / -1;
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
    this._filter = "last_30d";
    this._loading = true;
    this._error = null;
    this._cycleTime = null;
    this._leadTimeTrend = null;
    this._wip = null;
    this._costPerIssue = null;
    this._weeklyCost = null;
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

  private _setFilter(filter: QuickFilter): void {
    this._filter = filter;
    this._fetchAll();
  }

  private async _fetchAll(): Promise<void> {
    this._loading = true;
    this._error = null;
    try {
      const tf = (column: string) => timeFilter(column, this._filter);

      const [
        agentTable,
        cycleTable,
        leadTable,
        wipTable,
        costTable,
        weeklyTable,
        reworkTable,
        strandedTable,
        decisionTable,
      ] = await Promise.all([
        this._queryAgentNames(),
        this._queryCycleTime(tf),
        this._queryLeadTimeTrend(tf),
        this._queryWip(),
        this._queryCostPerIssue(tf),
        this._queryWeeklyCost(tf),
        query(this.apiBase, SQL_REWORK_RATE),
        query(this.apiBase, SQL_STRANDED),
        query(this.apiBase, SQL_DECISION_QUEUE),
      ]);

      const nameMap = new Map<string, string>(
        (arrowToRows(agentTable) as Array<{ agent_id: string; agent_name: string }>).map((row) => [
          row.agent_id,
          row.agent_name,
        ]),
      );

      this._cycleTime = (arrowToRows(cycleTable) as CycleTimeRow[]).map((row) => ({
        ...row,
        agent_id: agentLabel(String(row.agent_id), nameMap),
      }));
      this._leadTimeTrend = arrowToRows(leadTable) as LeadTimeTrendRow[];
      this._wip = arrowToRows(wipTable) as WipRow[];
      this._costPerIssue = (arrowToRows(costTable) as CostPerIssueRow[]).map((row) => ({
        ...row,
        agent_id: agentLabel(String(row.agent_id), nameMap),
      }));
      this._weeklyCost = arrowToRows(weeklyTable) as WeeklyCostRow[];
      this._reworkRows = arrowToRows(reworkTable);
      this._strandedRows = arrowToRows(strandedTable);
      this._decisionRows = arrowToRows(decisionTable);
    } catch (error) {
      this._error = (error as Error).message;
    }
    this._loading = false;
  }

  private _queryAgentNames(): Promise<Table> {
    return query(
      this.apiBase,
      `SELECT DISTINCT ON (agent_id) agent_id, COALESCE(name, agent_id) AS agent_name
       FROM sources.paperclip_agents
       ORDER BY agent_id, _dlt_valid_from DESC`,
    );
  }

  private _queryCycleTime(tf: (col: string) => string): Promise<Table> {
    return query(
      this.apiBase,
      `SELECT
        COALESCE(agent_at_terminal, 'unassigned') AS agent_id,
        ROUND(
          CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY epoch(terminal_at::TIMESTAMP - first_in_progress_at::TIMESTAMP)
          ) AS DOUBLE) / 3600.0, 2
        ) AS p50_hours,
        ROUND(
          CAST(PERCENTILE_CONT(0.9) WITHIN GROUP (
            ORDER BY epoch(terminal_at::TIMESTAMP - first_in_progress_at::TIMESTAMP)
          ) AS DOUBLE) / 3600.0, 2
        ) AS p90_hours,
        COUNT(*) AS issue_count
      FROM datasets.paperclip_kpi__dim_issue_terminal
      WHERE final_status = 'done'
        AND first_in_progress_at IS NOT NULL
        AND terminal_at IS NOT NULL
        AND ${tf("terminal_at")}
      GROUP BY agent_at_terminal
      ORDER BY p50_hours ASC`,
    );
  }

  private _queryLeadTimeTrend(tf: (col: string) => string): Promise<Table> {
    return query(
      this.apiBase,
      `SELECT
        strftime(DATE_TRUNC('week', terminal_at::TIMESTAMP), '%Y-%m-%d') AS week,
        ROUND(
          CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY epoch(terminal_at::TIMESTAMP - created_at::TIMESTAMP)
          ) AS DOUBLE) / 3600.0, 2
        ) AS p50_lead_hours
      FROM datasets.paperclip_kpi__dim_issue_terminal
      WHERE final_status = 'done'
        AND terminal_at IS NOT NULL
        AND created_at IS NOT NULL
        AND ${tf("terminal_at")}
      GROUP BY DATE_TRUNC('week', terminal_at::TIMESTAMP)
      ORDER BY week`,
    );
  }

  private _queryWip(): Promise<Table> {
    return query(
      this.apiBase,
      `WITH latest_per_issue AS (
        SELECT DISTINCT ON (issue_id) issue_id, to_status AS current_status
        FROM datasets.paperclip_kpi__fact_issue_lifecycle
        ORDER BY issue_id, transition_ts DESC
      )
      SELECT current_status AS status, CAST(COUNT(*) AS INTEGER) AS count
      FROM latest_per_issue
      WHERE current_status NOT IN ('done', 'cancelled')
      GROUP BY current_status
      ORDER BY count DESC`,
    );
  }

  private _queryCostPerIssue(tf: (col: string) => string): Promise<Table> {
    return query(
      this.apiBase,
      `SELECT
        COALESCE(agent_at_terminal, 'unassigned') AS agent_id,
        ROUND(AVG(COALESCE(total_cost_usd_attributed, 0.0)), 4) AS avg_cost_usd,
        COUNT(*) AS issue_count
      FROM datasets.paperclip_kpi__dim_issue_terminal
      WHERE final_status = 'done'
        AND ${tf("terminal_at")}
      GROUP BY agent_at_terminal
      ORDER BY avg_cost_usd DESC`,
    );
  }

  private _queryWeeklyCost(tf: (col: string) => string): Promise<Table> {
    return query(
      this.apiBase,
      `SELECT
        strftime(DATE_TRUNC('week', started_at::TIMESTAMP), '%Y-%m-%d') AS week,
        ROUND(SUM(COALESCE(cost_usd, 0.0)), 4) AS total_cost_usd
      FROM datasets.paperclip_kpi__fact_run_cost
      WHERE started_at IS NOT NULL
        AND ${tf("started_at")}
      GROUP BY DATE_TRUNC('week', started_at::TIMESTAMP)
      ORDER BY week`,
    );
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

  _renderChartsGrid(): TemplateResult {
    const cycleLabels = this._cycleTime?.map((row) => row.agent_id) ?? [];
    const cycleP50: KpiSeries = {
      name: "p50",
      values: this._cycleTime?.map((row) => Number(row.p50_hours)) ?? [],
      color: "#4a90d9",
    };
    const cycleP90: KpiSeries = {
      name: "p90",
      values: this._cycleTime?.map((row) => Number(row.p90_hours)) ?? [],
      color: "#e74c3c",
    };

    const leadWeeks = this._leadTimeTrend?.map((row) => row.week) ?? [];
    const leadSeries: KpiSeries = {
      name: "lead time (h)",
      values: this._leadTimeTrend?.map((row) => Number(row.p50_lead_hours)) ?? [],
      color: "#27ae60",
    };

    const wipLabels = this._wip?.map((row) => row.status) ?? [];
    const wipSeries: KpiSeries = {
      name: "issues",
      values: this._wip?.map((row) => Number(row.count)) ?? [],
      color: "#8e44ad",
    };

    const costLabels = this._costPerIssue?.map((row) => row.agent_id) ?? [];
    const costSeries: KpiSeries = {
      name: "avg cost (USD)",
      values: this._costPerIssue?.map((row) => Number(row.avg_cost_usd)) ?? [],
      color: "#e67e22",
    };

    const weeklyLabels = this._weeklyCost?.map((row) => row.week) ?? [];
    const weeklySeries: KpiSeries = {
      name: "cost (USD)",
      values: this._weeklyCost?.map((row) => Number(row.total_cost_usd)) ?? [],
      color: "#6b5ce7",
    };

    return html`
      <div class="grid">
        <kpi-chart
          title="Cycle Time by Agent (hours)"
          type="bar-h"
          .labels=${cycleLabels}
          .series=${[cycleP50, cycleP90]}
          y-label="hours"
        ></kpi-chart>
        <kpi-chart
          title="Lead-Time Trend (p50 hours, weekly)"
          type="line"
          .labels=${leadWeeks}
          .series=${[leadSeries]}
          y-label="hours"
        ></kpi-chart>
        <kpi-chart
          title="WIP Count by Status"
          type="bar-h"
          .labels=${wipLabels}
          .series=${[wipSeries]}
          y-label="count"
        ></kpi-chart>
        <kpi-chart
          title="Cost per Closed Issue by Agent (USD)"
          type="bar-h"
          .labels=${costLabels}
          .series=${[costSeries]}
          y-label="USD"
        ></kpi-chart>
        <div class="full-width">
          <kpi-chart
            title="Weekly Cost Trend (USD)"
            type="line"
            .labels=${weeklyLabels}
            .series=${[weeklySeries]}
            y-label="USD"
          ></kpi-chart>
        </div>
      </div>
    `;
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
    if (this._loading) return html`<div class="loading">Loading KPI data…</div>`;
    if (this._error) return html`<div class="error">Error: ${this._error}</div>`;

    return html`
      <div class="header">
        <h1>Paperclip KPI</h1>
        <div class="filters">
          ${QUICK_FILTERS.map(
            (f) => html`
              <button
                class="filter-btn ${this._filter === f.key ? "active" : ""}"
                @click=${() => this._setFilter(f.key)}
              >
                ${f.label}
              </button>
            `,
          )}
        </div>
      </div>
      <p class="subtitle">Cycle time, lead time, WIP, cost, rework rate, stranded issues, and decision throughput</p>
      ${this._renderChartsGrid()} ${this._renderReworkSection()} ${this._renderStrandedSection()}
      ${this._renderDecisionQueueSection()}
    `;
  }
}

customElements.define("shenas-kpi-dashboard", ShenasKpiDashboard);
