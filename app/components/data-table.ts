import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult, PropertyValues } from "lit";
import { gql, query as arrowQuery, arrowToRows } from "shenas-frontends";
import type { RowData } from "shenas-frontends";
import * as echarts from "echarts/core";
import { LineChart, BarChart, ScatterChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

interface TableInfo {
  schema: string;
  table: string;
}

interface ColMeta {
  dbType: string;
  description: string;
  displayName: string;
  unit: string;
  nullable: boolean;
  valueRange: number[] | null;
  exampleValue: string;
  interpretation: string;
}

export class ShenasDataTable extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    schema: { type: String },
    table: { type: String },
    pageSize: { type: Number, attribute: "page-size" },
    _tables: { state: true },
    _selectedTable: { state: true },
    _columns: { state: true },
    _data: { state: true },
    _sortCol: { state: true },
    _sortDesc: { state: true },
    _filters: { state: true },
    _searchTerm: { state: true },
    _page: { state: true },
    _colWidths: { state: true },
    _colMeta: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _dataView: { state: true },
    _tableKind: { state: true },
    _timeColumns: { state: true },
  };

  declare apiBase: string;
  declare schema: string;
  declare table: string;
  declare pageSize: number;
  declare _tables: TableInfo[];
  declare _selectedTable: string;
  declare _columns: string[];
  declare _data: RowData[];
  declare _sortCol: string | null;
  declare _sortDesc: boolean;
  declare _filters: Record<string, string>;
  declare _searchTerm: string;
  declare _page: number;
  declare _colWidths: Record<string, number>;
  declare _colMeta: Record<string, ColMeta>;
  declare _loading: boolean;
  declare _error: string | null;
  declare _dataView: "table" | "stats" | "graph";
  declare _tableKind: string | null;
  declare _timeColumns: {
    timeAt?: string;
    timeStart?: string;
    timeEnd?: string;
    cursorColumn?: string;
    observedAtInjected?: boolean;
  } | null;

  static styles: CSSResult = css`
    :host {
      display: flex;
      flex-direction: column;
      font-family:
        system-ui,
        -apple-system,
        sans-serif;
      height: 100%;
      overflow: hidden;
    }
    h1 {
      font-size: 20px;
      font-weight: 600;
      color: #222;
      margin: 0 0 12px 0;
    }
    .controls {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      flex-shrink: 0;
    }
    select,
    input {
      padding: 4px 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 12px;
    }
    select {
      min-width: 200px;
    }
    .compact-select {
      margin-bottom: 6px;
      font-size: 12px;
      padding: 3px 6px;
    }
    .table-wrap {
      overflow: auto;
      flex: 1;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      background: #fff;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      font-size: 12px;
      table-layout: fixed;
    }
    th {
      position: relative;
      background: #f5f5f5;
      border-bottom: 1px solid #ddd;
      padding: 4px 8px;
      text-align: left;
      font-weight: 600;
      color: #555;
      white-space: nowrap;
      overflow: hidden;
      cursor: pointer;
      user-select: none;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    th:hover {
      background: #eee;
    }
    .sort-indicator {
      margin-left: 3px;
      color: #999;
    }
    .resize-handle {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      cursor: col-resize;
    }
    .resize-handle:hover {
      background: #4a90d9;
    }
    td {
      padding: 3px 8px;
      border-bottom: 1px solid #f0f0f0;
      color: #444;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    tr:hover td {
      background: #f8f8ff;
    }
    .pagination {
      display: flex;
      gap: 6px;
      align-items: center;
      padding: 4px 0;
      font-size: 11px;
      color: #888;
      flex-shrink: 0;
    }
    .pagination button {
      padding: 2px 8px;
      border: 1px solid #ddd;
      border-radius: 3px;
      background: #fff;
      cursor: pointer;
      font-size: 11px;
    }
    .pagination button:disabled {
      opacity: 0.4;
      cursor: default;
    }
    .pagination button:not(:disabled):hover {
      background: #f0f0f0;
    }
    .page-link.active {
      background: #728f67;
      color: #fff;
      border-color: #728f67;
    }
    .page-ellipsis {
      color: #aaa;
      font-size: 11px;
      padding: 0 2px;
    }
    .page-jump {
      width: 50px;
      padding: 2px 4px;
      font-size: 11px;
      border: 1px solid #ddd;
      border-radius: 3px;
      text-align: center;
    }
    .page-jump::-webkit-inner-spin-button {
      -webkit-appearance: none;
    }
    .loading {
      color: #888;
      padding: 24px;
      text-align: center;
    }
    .error {
      color: #c00;
      background: #fee;
      padding: 12px;
      border-radius: 6px;
    }
    .page-info {
      flex: 1;
      text-align: center;
    }
    .search-bar {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 0;
      flex-shrink: 0;
    }
    .search-bar input {
      flex: 1;
      padding: 3px 8px;
      font-size: 12px;
      border: 1px solid #ddd;
      border-radius: 3px;
    }
    .view-toggle {
      display: flex;
      gap: 2px;
    }
    .view-toggle button {
      background: none;
      border: 1px solid #ddd;
      border-radius: 3px;
      padding: 3px 6px;
      cursor: pointer;
      color: #999;
      line-height: 1;
      display: flex;
      align-items: center;
    }
    .view-toggle button:hover {
      background: #f0f0f0;
      color: #555;
    }
    .view-toggle button[aria-pressed="true"] {
      background: #728f67;
      color: #fff;
      border-color: #728f67;
    }
    .view-toggle svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }
    .stats-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .stats-table th {
      cursor: default;
    }
    .stats-table td {
      padding: 4px 8px;
      border-bottom: 1px solid #f0f0f0;
      white-space: nowrap;
    }
    .chart-wrap {
      flex: 1;
      min-height: 300px;
    }
    .chart-hint {
      color: #aaa;
      font-size: 11px;
      padding: 4px 0;
      flex-shrink: 0;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this.schema = "";
    this.table = "";
    this.pageSize = 25;
    this._tables = [];
    this._selectedTable = "";
    this._columns = [];
    this._data = [];
    this._sortCol = null;
    this._sortDesc = false;
    this._filters = {};
    this._searchTerm = "";
    this._page = 0;
    this._colWidths = {};
    this._colMeta = {};
    this._loading = false;
    this._error = null;
    this._dataView = "table";
    this._tableKind = null;
    this._timeColumns = null;
  }

  private _chart: echarts.ECharts | null = null;
  private _ro: ResizeObserver | null = null;

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._chart) {
      this._chart.dispose();
      this._chart = null;
    }
    if (this._ro) {
      this._ro.disconnect();
      this._ro = null;
    }
  }

  updated(changed: PropertyValues): void {
    if (this._dataView === "graph" && (changed.has("_dataView") || changed.has("_data") || changed.has("_tableKind"))) {
      // Defer to next frame so the chart-wrap div is in the DOM
      requestAnimationFrame(() => this._buildChart());
    }
    if (changed.has("_dataView") && this._dataView !== "graph" && this._chart) {
      this._chart.dispose();
      this._chart = null;
    }
  }

  connectedCallback(): void {
    super.connectedCallback();
    if (this.table && this.schema) {
      this._selectedTable = `${this.schema}.${this.table}`;
      this._fetchData();
    } else {
      this._fetchTables();
    }
  }

  willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("table") && this.table && this.schema) {
      this._selectedTable = `${this.schema}.${this.table}`;
      this._fetchData();
    }
  }

  async _fetchTables(): Promise<void> {
    try {
      const res = await fetch(`${this.apiBase}/tables`);
      let tables: TableInfo[] = await res.json();
      tables = tables.filter((t) => !t.table.startsWith("_dlt_"));
      if (this.schema) {
        tables = tables.filter((t) => t.schema === this.schema);
      }
      this._tables = tables;
      if (this._tables.length > 0) {
        this._selectedTable = `${this._tables[0].schema}.${this._tables[0].table}`;
        this._fetchData();
      }
    } catch (e) {
      this._error = (e as Error).message;
    }
  }

  async _fetchData(): Promise<void> {
    this._loading = true;
    this._error = null;
    try {
      const sql = `SELECT * FROM ${this._selectedTable}`;
      const table = await arrowQuery(this.apiBase, sql);

      this._columns = table.schema.fields.map((f) => f.name).filter((c) => !c.startsWith("_dlt_"));
      this._data = arrowToRows(table);

      // Fetch column type metadata and table-level metadata in parallel
      const [s, t] = this._selectedTable.split(".");
      const [colResult, metaResult] = await Promise.all([
        gql(
          this.apiBase,
          `query($s: String!, $t: String!) { tableColumnInfo(schema: $s, table: $t) { name dbType displayName description unit nullable valueRange exampleValue interpretation } }`,
          { s, t },
        ),
        gql(
          this.apiBase,
          `query($s: String!, $t: String!) { tableInfo(schema: $s, table: $t) { kind timeColumns { timeAt timeStart timeEnd cursorColumn observedAtInjected } queryHint } }`,
          { s, t },
        ),
      ]);
      this._colMeta = {};
      for (const c of (colResult?.tableColumnInfo || []) as Array<ColMeta & { name: string }>) {
        this._colMeta[c.name] = c;
      }
      const tm = metaResult?.tableInfo as Record<string, unknown> | undefined;
      this._tableKind = (tm?.kind as string) || null;
      this._timeColumns = (tm?.timeColumns as typeof this._timeColumns) || null;
      this._page = 0;
      this._filters = {};
      this._searchTerm = "";
      this._sortCol = null;
    } catch (e) {
      this._error = (e as Error).message;
    }
    this._loading = false;
  }

  get _filteredData(): RowData[] {
    let data = this._data;
    const term = this._searchTerm.toLowerCase();
    if (term) {
      data = data.filter((row) =>
        this._columns.some((col) => {
          const cell = row[col];
          return cell != null && String(cell).toLowerCase().includes(term);
        }),
      );
    }
    const filters = this._filters;
    for (const col of Object.keys(filters)) {
      const v = filters[col]?.toLowerCase();
      if (!v) continue;
      data = data.filter((row) => {
        const cell = row[col];
        return cell != null && String(cell).toLowerCase().includes(v);
      });
    }
    return data;
  }

  get _sortedData(): RowData[] {
    const data = [...this._filteredData];
    if (!this._sortCol) return data;
    const col = this._sortCol;
    const desc = this._sortDesc;
    return data.sort((a, b) => {
      const va = a[col],
        vb = b[col];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return desc ? 1 : -1;
      if (va > vb) return desc ? -1 : 1;
      return 0;
    });
  }

  get _pagedData(): RowData[] {
    const start = this._page * this.pageSize;
    return this._sortedData.slice(start, start + this.pageSize);
  }

  get _pageCount(): number {
    return Math.max(1, Math.ceil(this._sortedData.length / this.pageSize));
  }

  _onTableChange(e: Event): void {
    this._selectedTable = (e.target as HTMLSelectElement).value;
    this._fetchData();
  }

  _onSort(col: string): void {
    if (this._sortCol === col) {
      this._sortDesc = !this._sortDesc;
    } else {
      this._sortCol = col;
      this._sortDesc = false;
    }
  }

  _onFilter(col: string, value: string): void {
    this._filters = { ...this._filters, [col]: value };
    this._page = 0;
  }

  _formatCell(value: unknown, col?: string): string {
    if (value == null) return "";
    const dbType = col ? (this._colMeta[col]?.dbType || "").toUpperCase() : "";
    const isTimestamp = dbType.includes("TIMESTAMP");
    const isDate = dbType === "DATE";
    if (value instanceof Date) {
      return isDate ? value.toISOString().slice(0, 10) : value.toISOString().replace("T", " ").slice(0, 19);
    }
    if (typeof value === "bigint") {
      if (isTimestamp) {
        // bigint timestamps: >1e15 = microseconds, >1e12 = milliseconds, else seconds
        let ms: number;
        if (value > 1_000_000_000_000_000n) ms = Number(value / 1000n);
        else if (value > 1_000_000_000_000n) ms = Number(value);
        else ms = Number(value) * 1000;
        return new Date(ms).toISOString().replace("T", " ").slice(0, 19);
      }
      return value.toString();
    }
    if (typeof value === "number" && isTimestamp) {
      // number timestamps: >1e15 = microseconds, >1e12 = milliseconds, else seconds
      let ms: number;
      if (value > 1e15) ms = value / 1000;
      else if (value > 1e12) ms = value;
      else ms = value * 1000;
      return new Date(ms).toISOString().replace("T", " ").slice(0, 19);
    }
    return String(value);
  }

  _onResizeStart(e: MouseEvent, col: string): void {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startWidth = this._colWidths[col] || 150;
    const onMove = (ev: MouseEvent): void => {
      this._colWidths = { ...this._colWidths, [col]: Math.max(50, startWidth + ev.clientX - startX) };
    };
    const onUp = (): void => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  render(): TemplateResult {
    if (this._error) return html`<div class="error">${this._error}</div>`;

    const tableSelector = this.table
      ? ""
      : this.schema
        ? html`<select class="compact-select" @change=${this._onTableChange}>
            ${this._tables.map(
              (t) => html`
                <option value="${t.schema}.${t.table}" ?selected=${`${t.schema}.${t.table}` === this._selectedTable}>
                  ${t.table}
                </option>
              `,
            )}
          </select>`
        : html`<div class="controls">
            <h1>data table</h1>
            <select @change=${this._onTableChange}>
              ${this._tables.map(
                (t) => html`
                  <option value="${t.schema}.${t.table}" ?selected=${`${t.schema}.${t.table}` === this._selectedTable}>
                    ${t.schema}.${t.table}
                  </option>
                `,
              )}
            </select>
          </div>`;

    if (this._loading)
      return html`${tableSelector}
        <div class="loading">Loading...</div>`;
    if (this._data.length === 0)
      return html`${tableSelector}
        <div class="loading">No data</div>`;

    const rows = this._pagedData;

    // Hide numeric-only "id" columns that are just PKs
    const visibleCols = this._columns.filter(
      (c) => !(c === "id" && this._data.length > 0 && typeof this._data[0][c] === "number"),
    );

    return html`
      ${tableSelector}
      <div class="search-bar">
        <input
          type="text"
          placeholder="Search..."
          .value=${this._searchTerm}
          @input=${(e: Event) => {
            this._searchTerm = (e.target as HTMLInputElement).value;
            this._page = 0;
          }}
        />
        <span style="color:#aaa;font-size:11px">${this._sortedData.length} rows</span>
        <div class="view-toggle">
          <button
            title="Descriptive Statistics"
            aria-pressed=${this._dataView === "stats"}
            @click=${() => (this._dataView = "stats")}
          >
            <svg viewBox="0 0 24 24">
              <path d="M3 3v18h18v-2H5V3H3zm14 4h-4v12h4V7zm-6 4H7v8h4v-8zm12-2h-4v10h4V9z" />
            </svg>
          </button>
          <button title="Table" aria-pressed=${this._dataView === "table"} @click=${() => (this._dataView = "table")}>
            <svg viewBox="0 0 24 24">
              <path d="M3 3h18v18H3V3zm2 4v4h6V7H5zm8 0v4h6V7h-6zM5 13v4h6v-4H5zm8 0v4h6v-4h-6z" />
            </svg>
          </button>
          <button title="Graph" aria-pressed=${this._dataView === "graph"} @click=${() => (this._dataView = "graph")}>
            <svg viewBox="0 0 24 24"><path d="M3.5 18.5l6-6 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z" /></svg>
          </button>
        </div>
      </div>
      ${this._dataView === "table" ? this._renderTableView(visibleCols, rows) : ""}
      ${this._dataView === "stats" ? this._renderStatsView(visibleCols) : ""}
      ${this._dataView === "graph" ? this._renderGraphView() : ""}
    `;
  }

  _renderTableView(visibleCols: string[], rows: RowData[]): TemplateResult {
    return html`
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${visibleCols.map(
                (col) => html`
                  <th
                    style="width:${this._colWidths[col] || 120}px"
                    title="${this._colTooltip(col)}"
                    @click=${() => this._onSort(col)}
                  >
                    ${this._colMeta[col]?.displayName || col}
                    ${this._sortCol === col
                      ? html`<span class="sort-indicator">${this._sortDesc ? "v" : "^"}</span>`
                      : ""}
                    <div class="resize-handle" @mousedown=${(e: MouseEvent) => this._onResizeStart(e, col)}></div>
                  </th>
                `,
              )}
            </tr>
          </thead>
          <tbody>
            ${rows.map(
              (row) => html`
                <tr>
                  ${visibleCols.map(
                    (col) =>
                      html`<td style="width:${this._colWidths[col] || 120}px">${this._formatCell(row[col], col)}</td>`,
                  )}
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button ?disabled=${this._page === 0} @click=${() => (this._page = 0)} title="First">&laquo;</button>
        <button ?disabled=${this._page === 0} @click=${() => this._page--}>&lsaquo;</button>
        ${this._renderPageLinks()}
        <button ?disabled=${this._page >= this._pageCount - 1} @click=${() => this._page++}>&rsaquo;</button>
        <button
          ?disabled=${this._page >= this._pageCount - 1}
          @click=${() => (this._page = this._pageCount - 1)}
          title="Last"
        >
          &raquo;
        </button>
        ${this._pageCount > 10
          ? html`<input
              type="number"
              class="page-jump"
              min="1"
              max=${this._pageCount}
              placeholder="Go to"
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === "Enter") {
                  const v = parseInt((e.target as HTMLInputElement).value);
                  if (v >= 1 && v <= this._pageCount) this._page = v - 1;
                  (e.target as HTMLInputElement).value = "";
                }
              }}
            />`
          : ""}
      </div>
    `;
  }

  _renderStatsView(visibleCols: string[]): TemplateResult {
    const data = this._sortedData;

    const stats = visibleCols.map((col) => {
      const values = data.map((r) => r[col]);
      const nonNull = values.filter((v) => v != null);
      const count = nonNull.length;
      const nullCount = values.length - count;
      const unique = new Set(nonNull.map(String)).size;

      const numericValues = nonNull.map(Number).filter((n) => !Number.isNaN(n));
      const isNumeric = numericValues.length > count * 0.5 && numericValues.length > 0;

      if (isNumeric) {
        const sorted = [...numericValues].sort((a, b) => a - b);
        const sum = sorted.reduce((a, b) => a + b, 0);
        const mean = sum / sorted.length;
        const min = sorted[0];
        const max = sorted[sorted.length - 1];
        const median =
          sorted.length % 2 === 0
            ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
            : sorted[Math.floor(sorted.length / 2)];
        const variance = sorted.reduce((acc, v) => acc + (v - mean) ** 2, 0) / sorted.length;
        const stddev = Math.sqrt(variance);
        const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));
        return {
          col,
          type: "numeric" as const,
          count,
          nullCount,
          unique,
          min: fmt(min),
          max: fmt(max),
          mean: fmt(mean),
          median: fmt(median),
          stddev: fmt(stddev),
        };
      }
      const freqMap = new Map<string, number>();
      for (const v of nonNull) {
        const k = String(v);
        freqMap.set(k, (freqMap.get(k) || 0) + 1);
      }
      const top = freqMap.size > 0 ? [...freqMap.entries()].sort((a, b) => b[1] - a[1])[0] : null;
      return { col, type: "text" as const, count, nullCount, unique, top: top ? `${top[0]} (${top[1]})` : "-" };
    });

    return html`
      <div class="table-wrap">
        <table class="stats-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Type</th>
              <th>Non-null</th>
              <th>Null</th>
              <th>Unique</th>
              <th>Min</th>
              <th>Max</th>
              <th>Mean</th>
              <th>Median</th>
              <th>Std Dev</th>
              <th>Top Value</th>
            </tr>
          </thead>
          <tbody>
            ${stats.map(
              (s) => html`
                <tr>
                  <td>${this._colMeta[s.col]?.displayName || s.col}</td>
                  <td>${s.type}</td>
                  <td>${s.count}</td>
                  <td>${s.nullCount}</td>
                  <td>${s.unique}</td>
                  <td>${s.type === "numeric" ? s.min : "-"}</td>
                  <td>${s.type === "numeric" ? s.max : "-"}</td>
                  <td>${s.type === "numeric" ? s.mean : "-"}</td>
                  <td>${s.type === "numeric" ? s.median : "-"}</td>
                  <td>${s.type === "numeric" ? s.stddev : "-"}</td>
                  <td>${s.type === "text" ? s.top : "-"}</td>
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderGraphView(): TemplateResult {
    const kind = this._tableKind;
    const hint = kind ? `Table kind: ${kind}` : "";
    return html`
      ${hint ? html`<div class="chart-hint">${hint}</div>` : ""}
      <div class="chart-wrap"></div>
    `;
  }

  _getTimeColumn(): string | null {
    const tc = this._timeColumns;
    // GQL returns camelCase; the actual DB column names are snake_case
    if (tc?.timeAt) return tc.timeAt;
    if (tc?.timeStart) return tc.timeStart;
    if (tc?.observedAtInjected && this._columns.includes("observed_at")) return "observed_at";
    // Fallback: look for common timestamp columns in the data
    for (const name of ["time_at", "date", "timestamp", "created_at", "observed_at", "time_start"]) {
      if (this._columns.includes(name)) return name;
    }
    // Try first TIMESTAMP/DATE column from colMeta
    for (const col of this._columns) {
      const dbType = (this._colMeta[col]?.dbType || "").toUpperCase();
      if (dbType.includes("TIMESTAMP") || dbType === "DATE") return col;
    }
    return null;
  }

  _getNumericColumns(): string[] {
    return this._columns.filter((col) => {
      const dbType = (this._colMeta[col]?.dbType || "").toUpperCase();
      if (
        dbType.includes("INT") ||
        dbType.includes("FLOAT") ||
        dbType.includes("DOUBLE") ||
        dbType.includes("DECIMAL") ||
        dbType.includes("NUMERIC") ||
        dbType === "BIGINT"
      ) {
        return true;
      }
      // Fallback: check actual data
      if (!dbType && this._data.length > 0) {
        const sample = this._data.slice(0, 10);
        return sample.some((r) => typeof r[col] === "number" || typeof r[col] === "bigint");
      }
      return false;
    });
  }

  _toTimestamp(value: unknown): number | null {
    if (value == null) return null;
    if (value instanceof Date) return value.getTime();
    if (typeof value === "bigint") {
      if (value > 1_000_000_000_000_000n) return Number(value / 1000n);
      if (value > 1_000_000_000_000n) return Number(value);
      return Number(value) * 1000;
    }
    if (typeof value === "number") {
      if (value > 1e15) return value / 1000;
      if (value > 1e12) return value;
      if (value > 1e9) return value * 1000;
      return value;
    }
    if (typeof value === "string") {
      const ms = Date.parse(value);
      return isNaN(ms) ? null : ms;
    }
    return null;
  }

  _buildChart(): void {
    const wrap = this.renderRoot.querySelector(".chart-wrap") as HTMLElement | null;
    if (!wrap || this._data.length === 0) return;

    if (this._chart) {
      this._chart.dispose();
      this._chart = null;
    }
    this._chart = echarts.init(wrap);

    const kind = this._tableKind;
    const timeCol = this._getTimeColumn();
    const numericCols = this._getNumericColumns().filter((c) => c !== timeCol && c !== "id");

    // Sort data by time column if available
    const rows = [...this._sortedData];
    if (timeCol) {
      rows.sort((a, b) => {
        const ta = this._toTimestamp(a[timeCol]);
        const tb = this._toTimestamp(b[timeCol]);
        if (ta == null && tb == null) return 0;
        if (ta == null) return 1;
        if (tb == null) return -1;
        return ta - tb;
      });
    }

    let option: echarts.EChartsCoreOption;

    if (kind === "event" || kind === "interval") {
      // Event/interval: scatter or count-over-time
      if (timeCol && numericCols.length > 0) {
        // Plot numeric columns over time
        const xData = rows.map((r) => {
          const ts = this._toTimestamp(r[timeCol]);
          return ts ? new Date(ts).toISOString().slice(0, 19).replace("T", " ") : "";
        });
        const series = numericCols.slice(0, 5).map((col) => ({
          name: this._colMeta[col]?.displayName || col,
          type: "scatter" as const,
          data: rows.map((r, i) => [xData[i], r[col] != null ? Number(r[col]) : null]),
          symbolSize: 4,
        }));
        option = this._timeSeriesOption(xData, series, "scatter");
      } else if (timeCol) {
        // No numeric columns: show event count by day
        option = this._countByDayOption(rows, timeCol);
      } else {
        option = this._fallbackBarOption(rows, numericCols);
      }
    } else if (
      kind === "aggregate" ||
      kind === "daily_metric" ||
      kind === "weekly_metric" ||
      kind === "monthly_metric"
    ) {
      // Aggregate/metric: line chart over time
      if (timeCol && numericCols.length > 0) {
        const xData = rows.map((r) => {
          const ts = this._toTimestamp(r[timeCol]);
          return ts ? new Date(ts).toISOString().slice(0, 10) : "";
        });
        const series = numericCols.slice(0, 5).map((col) => ({
          name: this._colMeta[col]?.displayName || col,
          type: "line" as const,
          data: rows.map((r) => (r[col] != null ? Number(r[col]) : null)),
          smooth: true,
          symbol: "none",
        }));
        option = this._timeSeriesOption(xData, series, "line");
      } else {
        option = this._fallbackBarOption(rows, numericCols);
      }
    } else if (kind === "counter") {
      // Counter: line chart showing value over observed_at
      if (timeCol && numericCols.length > 0) {
        const xData = rows.map((r) => {
          const ts = this._toTimestamp(r[timeCol]);
          return ts ? new Date(ts).toISOString().slice(0, 19).replace("T", " ") : "";
        });
        const series = numericCols.slice(0, 5).map((col) => ({
          name: this._colMeta[col]?.displayName || col,
          type: "line" as const,
          data: rows.map((r) => (r[col] != null ? Number(r[col]) : null)),
          step: "end" as const,
          symbol: "none",
        }));
        option = this._timeSeriesOption(xData, series, "line");
      } else {
        option = this._fallbackBarOption(rows, numericCols);
      }
    } else if (kind === "dimension" || kind === "snapshot") {
      // Dimension/snapshot: bar chart of categorical distribution
      option = this._categoryDistributionOption(rows);
    } else {
      // Unknown kind or null: best-effort auto-detect
      if (timeCol && numericCols.length > 0) {
        const xData = rows.map((r) => {
          const ts = this._toTimestamp(r[timeCol]);
          return ts ? new Date(ts).toISOString().slice(0, 10) : "";
        });
        const series = numericCols.slice(0, 5).map((col) => ({
          name: this._colMeta[col]?.displayName || col,
          type: "line" as const,
          data: rows.map((r) => (r[col] != null ? Number(r[col]) : null)),
          smooth: true,
          symbol: "none",
        }));
        option = this._timeSeriesOption(xData, series, "line");
      } else if (numericCols.length > 0) {
        option = this._fallbackBarOption(rows, numericCols);
      } else {
        option = this._categoryDistributionOption(rows);
      }
    }

    this._chart.setOption(option);

    if (!this._ro) {
      this._ro = new ResizeObserver(() => {
        if (this._chart) this._chart.resize();
      });
      this._ro.observe(wrap);
    }
  }

  _timeSeriesOption(
    xData: string[],
    series: Array<{ name: string; type: string; data: unknown[]; [k: string]: unknown }>,
    _chartType: string,
  ): echarts.EChartsCoreOption {
    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      legend: {
        show: series.length > 1,
        bottom: 0,
        textStyle: { fontSize: 11, color: "#888" },
        itemWidth: 12,
        itemHeight: 8,
      },
      grid: { left: 50, right: 16, top: 12, bottom: series.length > 1 ? 40 : 28, containLabel: false },
      xAxis: {
        type: "category",
        data: xData,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888" },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      dataZoom: [{ type: "inside", start: 0, end: 100 }],
      series,
    };
  }

  _countByDayOption(rows: RowData[], timeCol: string): echarts.EChartsCoreOption {
    const counts = new Map<string, number>();
    for (const r of rows) {
      const ts = this._toTimestamp(r[timeCol]);
      if (ts == null) continue;
      const day = new Date(ts).toISOString().slice(0, 10);
      counts.set(day, (counts.get(day) || 0) + 1);
    }
    const sorted = [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return this._timeSeriesOption(
      sorted.map((e) => e[0]),
      [{ name: "Count", type: "bar", data: sorted.map((e) => e[1]) }],
      "bar",
    );
  }

  _fallbackBarOption(rows: RowData[], numericCols: string[]): echarts.EChartsCoreOption {
    // Bar chart of first numeric column distribution
    const col = numericCols[0];
    if (!col) return this._categoryDistributionOption(rows);
    const values = rows
      .map((r) => r[col])
      .filter((v) => v != null)
      .map(Number)
      .filter((n) => !isNaN(n));
    if (values.length === 0) return this._categoryDistributionOption(rows);

    // Histogram: 20 bins
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binCount = 20;
    const binSize = (max - min) / binCount || 1;
    const bins = new Array<number>(binCount).fill(0);
    for (const v of values) {
      const idx = Math.min(Math.floor((v - min) / binSize), binCount - 1);
      bins[idx]++;
    }
    const labels = bins.map((_, i) => {
      const lo = min + i * binSize;
      return lo.toFixed(1);
    });
    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      grid: { left: 50, right: 16, top: 12, bottom: 28, containLabel: false },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888", rotate: 45 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      series: [
        { name: this._colMeta[col]?.displayName || col, type: "bar", data: bins, itemStyle: { color: "#728f67" } },
      ],
    };
  }

  _categoryDistributionOption(rows: RowData[]): echarts.EChartsCoreOption {
    // Find first non-id text column, count occurrences
    const textCol = this._columns.find((c) => {
      if (c === "id" || c.endsWith("_id")) return false;
      const dbType = (this._colMeta[c]?.dbType || "").toUpperCase();
      return (
        dbType.includes("VARCHAR") ||
        dbType.includes("TEXT") ||
        dbType === "" ||
        (!dbType.includes("INT") &&
          !dbType.includes("FLOAT") &&
          !dbType.includes("TIMESTAMP") &&
          !dbType.includes("DATE") &&
          !dbType.includes("BOOL"))
      );
    });
    if (!textCol) {
      return {
        title: {
          text: "No suitable columns for charting",
          left: "center",
          top: "center",
          textStyle: { fontSize: 13, color: "#aaa" },
        },
      };
    }
    const freq = new Map<string, number>();
    for (const r of rows) {
      const k = String(r[textCol] ?? "(null)");
      freq.set(k, (freq.get(k) || 0) + 1);
    }
    const sorted = [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      grid: { left: 16, right: 16, top: 12, bottom: 80, containLabel: true },
      xAxis: {
        type: "category",
        data: sorted.map((e) => e[0]),
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888", rotate: 45, interval: 0 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      series: [
        {
          name: this._colMeta[textCol]?.displayName || textCol,
          type: "bar",
          data: sorted.map((e) => e[1]),
          itemStyle: { color: "#728f67" },
        },
      ],
    };
  }

  _colTooltip(col: string): string {
    const m = this._colMeta[col];
    if (!m) return col;
    const lines: string[] = [];
    if (m.description) lines.push(m.description);
    const parts: string[] = [];
    if (m.dbType) parts.push(m.dbType);
    if (m.valueRange?.length) parts.push(`range: ${m.valueRange.join("-")}`);
    if (!m.nullable) parts.push("NOT NULL");
    if (m.exampleValue) parts.push(`e.g. ${m.exampleValue}`);
    if (m.unit) parts.push(`[${m.unit}]`);
    if (parts.length) lines.push(parts.join(", "));
    if (m.interpretation) lines.push(m.interpretation);
    return lines.join("\n");
  }

  _renderPageLinks(): TemplateResult {
    const total = this._pageCount;
    const cur = this._page;
    const pages: (number | "...")[] = [];

    if (total <= 7) {
      for (let i = 0; i < total; i++) pages.push(i);
    } else {
      pages.push(0);
      if (cur > 2) pages.push("...");
      for (let i = Math.max(1, cur - 1); i <= Math.min(total - 2, cur + 1); i++) pages.push(i);
      if (cur < total - 3) pages.push("...");
      pages.push(total - 1);
    }

    return html`${pages.map((p) =>
      p === "..."
        ? html`<span class="page-ellipsis">...</span>`
        : html`<button class="page-link ${p === cur ? "active" : ""}" @click=${() => (this._page = p as number)}>
            ${(p as number) + 1}
          </button>`,
    )}`;
  }
}

customElements.define("shenas-data-table", ShenasDataTable);
