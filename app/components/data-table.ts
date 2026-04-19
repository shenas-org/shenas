import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult, PropertyValues } from "lit";
import { getClient, gqlTag, query as arrowQuery, arrowToRows } from "shenas-frontends";
import type { RowData } from "shenas-frontends";
import * as echarts from "echarts/core";
import { LineChart, BarChart, ScatterChart, CustomChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

const GET_TABLE_METADATA = gqlTag`
  query GetTableMetadata($s: String!, $t: String!) {
    tableMetadata(schema: $s, table: $t)
  }
`;

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
    refreshKey: { type: String, attribute: "refresh-key" },
    tableMetadata: { type: Object, attribute: false },
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
    _infoMessage: { state: true },
    _dataView: { state: true },
    _tableKind: { state: true },
    _timeColumns: { state: true },
    _intervalMode: { state: true },
    _plotHints: { state: true },
  };

  declare apiBase: string;
  declare schema: string;
  declare table: string;
  declare pageSize: number;
  declare refreshKey: string;
  declare tableMetadata: Record<string, unknown> | null;
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
  declare _infoMessage: string | null;
  declare _dataView: "table" | "stats" | "graph";
  declare _tableKind: string | null;
  declare _timeColumns: {
    timeAt?: string;
    timeStart?: string;
    timeEnd?: string;
    cursorColumn?: string;
    observedAtInjected?: boolean;
  } | null;
  declare _intervalMode: "packed" | "concurrency" | "histogram";
  declare _plotHints: Array<{ y: string; groupBy?: string; chartType?: string; label?: string }> | null;

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
      right: -3px;
      top: 0;
      bottom: 0;
      width: 8px;
      cursor: col-resize;
      z-index: 2;
    }
    .resize-handle::after {
      content: "";
      position: absolute;
      right: 3px;
      top: 4px;
      bottom: 4px;
      width: 2px;
      background: #ddd;
    }
    .resize-handle:hover::after {
      background: #4a90d9;
      width: 3px;
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
    .info-message {
      color: var(--shenas-text-muted, #888);
      padding: 12px;
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
    .interval-graph {
      display: flex;
      flex: 1;
      gap: 8px;
      min-height: 300px;
    }
    .interval-mode-bar {
      display: flex;
      flex-direction: column;
      gap: 4px;
      width: 28px;
      flex-shrink: 0;
      padding-top: 2px;
    }
    .interval-mode-bar button {
      background: none;
      border: 1px solid #ddd;
      border-radius: 3px;
      padding: 4px 0;
      cursor: pointer;
      color: #999;
      font-size: 11px;
      font-weight: 600;
      line-height: 1;
    }
    .interval-mode-bar button:hover {
      background: #f0f0f0;
      color: #555;
    }
    .interval-mode-bar button[aria-pressed="true"] {
      background: #728f67;
      color: #fff;
      border-color: #728f67;
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
    this._infoMessage = null;
    this._dataView = "table";
    this._tableKind = null;
    this._timeColumns = null;
    this._intervalMode = "packed";
  }

  private _chart: echarts.ECharts | null = null;
  private _ro: ResizeObserver | null = null;
  private _histogramRecompute: ((winStart: number, winEnd: number) => void) | null = null;
  private _client = getClient();

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
    if (
      this._dataView === "graph" &&
      (changed.has("_dataView") || changed.has("_data") || changed.has("_tableKind") || changed.has("_intervalMode"))
    ) {
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
    if (changed.has("refreshKey") && this.refreshKey !== undefined && this._selectedTable) {
      this._fetchData();
    }
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
    this._infoMessage = null;
    try {
      const sql = `SELECT * FROM ${this._selectedTable}`;
      const table = await arrowQuery(this.apiBase, sql);

      this._columns = table.schema.fields.map((f) => f.name).filter((c) => !c.startsWith("_dlt_"));
      this._data = arrowToRows(table);

      // Use table metadata prop if available, otherwise fetch via GraphQL.
      let meta = this.tableMetadata as Record<string, unknown> | null;
      if (!meta?.columns) {
        const [schemaName, tableName] = this._selectedTable.split(".");
        const { data: result } = await this._client.query({
          query: GET_TABLE_METADATA,
          variables: { s: schemaName, t: tableName },
          fetchPolicy: "network-only",
        });
        meta = result?.tableMetadata as Record<string, unknown> | null;
      }
      this._applyTableMetadata(meta);
      this._page = 0;
      this._filters = {};
      this._searchTerm = "";
      this._sortCol = null;
    } catch (error) {
      const message = (error as Error).message || "";
      if (message.includes("does not exist")) {
        this._infoMessage = "Not synced yet. Sync this source to populate data.";
      } else {
        this._error = message;
      }
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
      if (isDate) {
        const ms = value > 100_000_000n ? Number(value) : Number(value) * 86_400_000;
        return new Date(ms).toISOString().slice(0, 10);
      }
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
    if (typeof value === "number" && isDate) {
      // DATE values from Arrow: days since epoch or milliseconds
      const ms = value > 1e8 ? value : value * 86_400_000;
      return new Date(ms).toISOString().slice(0, 10);
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
    if (this._infoMessage) return html`<div class="info-message">${this._infoMessage}</div>`;
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

        // Detect time columns and format as ISO instead of raw numbers.
        const dbType = (this._colMeta[col]?.dbType || "").toUpperCase();
        const isTime = dbType.includes("TIMESTAMP") || dbType === "DATE";
        const fmt = isTime
          ? (n: number) => {
              if (dbType === "DATE") {
                const ms = n > 1e8 ? n : n * 86_400_000;
                return new Date(ms).toISOString().slice(0, 10);
              }
              let ms: number;
              if (n > 1e15) ms = n / 1000;
              else if (n > 1e12) ms = n;
              else ms = n * 1000;
              return new Date(ms).toISOString().replace("T", " ").slice(0, 19);
            }
          : (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

        return {
          col,
          type: "numeric" as const,
          count,
          nullCount,
          unique,
          min: fmt(min),
          max: fmt(max),
          mean: isTime ? fmt(mean) : Number.isInteger(mean) ? String(mean) : mean.toFixed(2),
          median: isTime ? fmt(median) : Number.isInteger(median) ? String(median) : median.toFixed(2),
          stddev: isTime ? "-" : Number.isInteger(stddev) ? String(stddev) : stddev.toFixed(2),
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

    const timeRoles = this._getTimeRoles();
    const statsCols: { key: string; label: string; default: number; cell: (s: (typeof stats)[number]) => unknown }[] = [
      {
        key: "column",
        label: "Column",
        default: 200,
        cell: (s) => {
          const displayName = this._colMeta[s.col]?.displayName || s.col;
          const role = timeRoles[s.col];
          return role
            ? html`${displayName}
                <span
                  style="font-size:0.75rem;color:var(--shenas-text-muted,#888);background:var(--shenas-border-light,#f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px"
                  >${role}</span
                >`
            : displayName;
        },
      },
      { key: "type", label: "Type", default: 80, cell: (s) => s.type },
      { key: "count", label: "Non-null", default: 80, cell: (s) => s.count },
      { key: "nullCount", label: "Null", default: 60, cell: (s) => s.nullCount },
      { key: "unique", label: "Unique", default: 70, cell: (s) => s.unique },
      { key: "min", label: "Min", default: 90, cell: (s) => (s.type === "numeric" ? s.min : "-") },
      { key: "max", label: "Max", default: 90, cell: (s) => (s.type === "numeric" ? s.max : "-") },
      { key: "mean", label: "Mean", default: 90, cell: (s) => (s.type === "numeric" ? s.mean : "-") },
      { key: "median", label: "Median", default: 90, cell: (s) => (s.type === "numeric" ? s.median : "-") },
      { key: "stddev", label: "Std Dev", default: 90, cell: (s) => (s.type === "numeric" ? s.stddev : "-") },
      { key: "top", label: "Top Value", default: 200, cell: (s) => (s.type === "text" ? s.top : "-") },
    ];
    const widthOf = (c: (typeof statsCols)[number]) => this._colWidths[`__stats__${c.key}`] || c.default;

    const kind = this._tableKind;
    return html`
      ${kind ? html`<div class="chart-hint">Table kind: ${kind}</div>` : ""}
      <div class="table-wrap">
        <table class="stats-table">
          <thead>
            <tr>
              ${statsCols.map(
                (c) => html`
                  <th style="width:${widthOf(c)}px">
                    ${c.label}
                    <div
                      class="resize-handle"
                      @mousedown=${(e: MouseEvent) => this._onResizeStart(e, `__stats__${c.key}`)}
                    ></div>
                  </th>
                `,
              )}
            </tr>
          </thead>
          <tbody>
            ${stats.map(
              (s) => html`
                <tr>
                  ${statsCols.map((c) => html`<td style="width:${widthOf(c)}px">${c.cell(s)}</td>`)}
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
    const isInterval = kind === "interval" && !!this._timeColumns?.timeStart && !!this._timeColumns?.timeEnd;
    const modes: { id: "packed" | "concurrency" | "histogram"; label: string; title: string }[] = [
      { id: "packed", label: "P", title: "Packed timeline (greedy)" },
      { id: "concurrency", label: "C", title: "Concurrency (active count over time)" },
      { id: "histogram", label: "H", title: "Duration histogram" },
    ];
    const bar = isInterval
      ? html`<div class="interval-mode-bar">
          ${modes.map(
            (m) => html`
              <button
                title=${m.title}
                aria-pressed=${this._intervalMode === m.id}
                @click=${() => (this._intervalMode = m.id)}
              >
                ${m.label}
              </button>
            `,
          )}
        </div>`
      : "";
    return html`
      ${hint ? html`<div class="chart-hint">${hint}</div>` : ""}
      ${isInterval
        ? html`<div class="interval-graph">
            ${bar}
            <div class="chart-wrap"></div>
          </div>`
        : html`<div class="chart-wrap"></div>`}
    `;
  }

  _applyTableMetadata(meta: Record<string, unknown> | null): void {
    this._colMeta = {};
    if (meta?.columns) {
      for (const col of meta.columns as Array<Record<string, unknown>>) {
        const name = (col.name as string) || "";
        this._colMeta[name] = {
          dbType: (col.db_type as string) || "",
          displayName: (col.display_name as string) || "",
          description: (col.description as string) || "",
          unit: (col.unit as string) || "",
          nullable: (col.nullable as boolean) ?? true,
          valueRange: (col.value_range as number[]) || null,
          exampleValue: (col.example_value as string) || "",
          interpretation: (col.interpretation as string) || "",
        };
      }
    }
    this._tableKind = (meta?.kind as string) || null;
    const timeColumns = meta?.time_columns as Record<string, unknown> | undefined;
    this._timeColumns = timeColumns
      ? {
          timeAt: timeColumns.time_at as string | undefined,
          timeStart: timeColumns.time_start as string | undefined,
          timeEnd: timeColumns.time_end as string | undefined,
          cursorColumn: timeColumns.cursor_column as string | undefined,
          observedAtInjected: timeColumns.observed_at_injected as boolean | undefined,
        }
      : null;
    this._plotHints = (meta?.plot as typeof this._plotHints) || null;
  }

  _getTimeRoles(): Record<string, string> {
    const roles: Record<string, string> = {};
    const tc = this._timeColumns;
    if (!tc) return roles;
    if (tc.timeAt) roles[tc.timeAt] = "time";
    if (tc.timeStart) roles[tc.timeStart] = "start";
    if (tc.timeEnd) roles[tc.timeEnd] = "end";
    if (tc.cursorColumn && tc.cursorColumn !== tc.timeAt) roles[tc.cursorColumn] = "cursor";
    if (tc.observedAtInjected && this._columns.includes("observed_at")) roles["observed_at"] = "observed";
    return roles;
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
        dbType === "BIGINT" ||
        dbType === "BOOLEAN" ||
        dbType === "BOOL"
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
    this._histogramRecompute = null;
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

    if (this._plotHints?.length && timeCol) {
      // Use plot hints from table metadata
      const xData = rows.map((r) => {
        const ts = this._toTimestamp(r[timeCol]);
        return ts ? new Date(ts).toISOString().slice(0, 10) : "";
      });
      const series: Array<{
        name: string;
        type: string;
        data: Array<[string, number | null]> | Array<number | null>;
        smooth?: boolean;
        symbol?: string;
      }> = [];
      for (const hint of this._plotHints) {
        if (hint.groupBy) {
          const groups = new Map<string, Array<[string, number | null]>>();
          for (let i = 0; i < rows.length; i++) {
            const r = rows[i];
            const group = String(r[hint.groupBy] ?? "");
            if (!groups.has(group)) groups.set(group, []);
            groups.get(group)!.push([xData[i], r[hint.y] != null ? Number(r[hint.y]) : null]);
          }
          for (const [groupName, data] of groups) {
            series.push({
              name: `${hint.label || hint.y} (${groupName})`,
              type: hint.chartType || "line",
              data,
              smooth: true,
              symbol: "none",
            });
          }
        } else {
          series.push({
            name: hint.label || hint.y,
            type: hint.chartType || "line",
            data: rows.map((r) => (r[hint.y] != null ? Number(r[hint.y]) : null)),
            smooth: true,
            symbol: "none",
          });
        }
      }
      option = this._timeSeriesOption(xData, series, "line");
    } else if (kind === "interval") {
      const start = this._timeColumns?.timeStart;
      const end = this._timeColumns?.timeEnd;
      if (start && end) {
        switch (this._intervalMode) {
          case "concurrency":
            option = this._concurrencyOption(rows, start, end);
            break;
          case "histogram":
            option = this._durationHistogramOption(rows, start, end);
            break;
          default:
            option = this._packedTimelineOption(rows, start, end);
        }
      } else {
        option = this._fallbackBarOption(rows, numericCols);
      }
    } else if (kind === "event") {
      // Event: scatter or count-over-time
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

    const recompute: ((s: number, e: number) => void) | null = this._histogramRecompute;
    if (recompute) {
      this._chart.off("dataZoom");
      this._chart.on("dataZoom", () => {
        if (!this._chart) return;
        const opt = this._chart.getOption() as { dataZoom?: { startValue?: number; endValue?: number }[] };
        const dz = opt.dataZoom?.[0];
        if (dz?.startValue != null && dz?.endValue != null && recompute) {
          (recompute as (s: number, e: number) => void)(dz.startValue, dz.endValue);
        }
      });
    }

    if (!this._ro) {
      this._ro = new ResizeObserver(() => {
        if (this._chart) this._chart.resize();
      });
      this._ro.observe(wrap);
    }
  }

  _packedTimelineOption(rows: RowData[], startCol: string, endCol: string): echarts.EChartsCoreOption {
    type Bar = { start: number; end: number; lane: number };
    const intervals: { start: number; end: number }[] = [];
    for (const r of rows) {
      const s = this._toTimestamp(r[startCol]);
      const e = this._toTimestamp(r[endCol]);
      if (s == null || e == null) continue;
      intervals.push({ start: s, end: Math.max(e, s) });
    }
    if (intervals.length === 0) return this._fallbackBarOption(rows, []);

    intervals.sort((a, b) => a.start - b.start);
    const laneEnds: number[] = [];
    const bars: Bar[] = [];
    for (const iv of intervals) {
      let lane = laneEnds.findIndex((end) => end <= iv.start);
      if (lane === -1) {
        lane = laneEnds.length;
        laneEnds.push(iv.end);
      } else {
        laneEnds[lane] = iv.end;
      }
      bars.push({ start: iv.start, end: iv.end, lane });
    }
    const laneCount = laneEnds.length;
    const data = bars.map((b) => ({ value: [b.lane, b.start, b.end] }));
    const startFmt = this._colMeta[startCol]?.displayName || startCol;
    const endFmt = this._colMeta[endCol]?.displayName || endCol;

    return {
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { value: [number, number, number] };
          const [, s, e] = p.value;
          return [
            `${this._escapeHtml(startFmt)}: ${new Date(s).toLocaleString()}`,
            `${this._escapeHtml(endFmt)}: ${new Date(e).toLocaleString()}`,
            `Duration: ${this._formatDuration(Math.max(0, e - s))}`,
          ].join("<br/>");
        },
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      grid: { left: 24, right: 16, top: 12, bottom: 36, containLabel: false },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      yAxis: {
        type: "value",
        min: -0.5,
        max: laneCount - 0.5,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "slider", xAxisIndex: 0, height: 16, bottom: 8 },
      ],
      series: [
        {
          type: "custom",
          renderItem: (
            _params: unknown,
            api: {
              value: (i: number) => number;
              coord: (p: number[]) => number[];
              size: (p: number[]) => number[];
              style: () => unknown;
            },
          ) => {
            const laneIdx = api.value(0);
            const start = api.coord([api.value(1), laneIdx]);
            const endPoint = api.coord([api.value(2), laneIdx]);
            const height = Math.max(2, (api.size([0, 1])[1] ?? 8) * 0.7);
            const width = Math.max(1, endPoint[0] - start[0]);
            return {
              type: "rect",
              shape: { x: start[0], y: start[1] - height / 2, width, height },
              style: { ...(api.style() as object), fill: "#728f67", opacity: 0.85 },
            };
          },
          encode: { x: [1, 2], y: 0 },
          data,
        },
      ],
    };
  }

  _concurrencyOption(rows: RowData[], startCol: string, endCol: string): echarts.EChartsCoreOption {
    const events: { t: number; delta: number }[] = [];
    for (const r of rows) {
      const s = this._toTimestamp(r[startCol]);
      const e = this._toTimestamp(r[endCol]);
      if (s == null || e == null) continue;
      events.push({ t: s, delta: 1 });
      events.push({ t: Math.max(e, s), delta: -1 });
    }
    if (events.length === 0) return this._fallbackBarOption(rows, []);
    events.sort((a, b) => a.t - b.t || a.delta - b.delta);

    const points: [number, number][] = [];
    let active = 0;
    for (const ev of events) {
      active += ev.delta;
      const last = points[points.length - 1];
      if (last && last[0] === ev.t) {
        last[1] = active;
      } else {
        points.push([ev.t, active]);
      }
    }

    return {
      tooltip: {
        trigger: "axis",
        formatter: (params: unknown) => {
          const arr = params as { value: [number, number] }[];
          if (!arr.length) return "";
          const [t, v] = arr[0].value;
          return `${new Date(t).toLocaleString()}<br/>Active: <b>${v}</b>`;
        },
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
      },
      grid: { left: 48, right: 16, top: 12, bottom: 36, containLabel: false },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      yAxis: {
        type: "value",
        name: "active",
        nameTextStyle: { fontSize: 10, color: "#888" },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 10, color: "#888" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "slider", xAxisIndex: 0, height: 16, bottom: 8 },
      ],
      series: [
        {
          type: "line",
          step: "end",
          symbol: "none",
          areaStyle: { opacity: 0.3, color: "#728f67" },
          lineStyle: { color: "#728f67" },
          data: points,
        },
      ],
    };
  }

  _durationHistogramOption(rows: RowData[], startCol: string, endCol: string): echarts.EChartsCoreOption {
    type Iv = { start: number; end: number; dur: number };
    const intervals: Iv[] = [];
    for (const r of rows) {
      const s = this._toTimestamp(r[startCol]);
      const e = this._toTimestamp(r[endCol]);
      if (s == null || e == null) continue;
      const end = Math.max(e, s);
      const dur = end - s;
      if (dur > 0) intervals.push({ start: s, end, dur });
    }
    if (intervals.length === 0) return this._fallbackBarOption(rows, []);

    let minD = Infinity;
    let maxD = -Infinity;
    let minT = Infinity;
    let maxT = -Infinity;
    for (const iv of intervals) {
      if (iv.dur < minD) minD = iv.dur;
      if (iv.dur > maxD) maxD = iv.dur;
      if (iv.start < minT) minT = iv.start;
      if (iv.end > maxT) maxT = iv.end;
    }
    const binCount = 30;

    let edges: number[];
    if (maxD / Math.max(1, minD) > 100) {
      const lo = Math.log10(Math.max(1, minD));
      const hi = Math.log10(Math.max(maxD, minD + 1));
      const step = (hi - lo) / binCount;
      edges = Array.from({ length: binCount + 1 }, (_, i) => Math.pow(10, lo + i * step));
    } else {
      const step = (maxD - minD) / binCount || 1;
      edges = Array.from({ length: binCount + 1 }, (_, i) => minD + i * step);
    }

    const computeCounts = (winStart: number, winEnd: number): number[] => {
      const c = new Array(binCount).fill(0);
      for (const iv of intervals) {
        if (iv.end < winStart || iv.start > winEnd) continue;
        let idx = edges.findIndex((edge, i) => i > 0 && iv.dur <= edge) - 1;
        if (idx < 0) idx = 0;
        if (idx >= binCount) idx = binCount - 1;
        c[idx]++;
      }
      return c;
    };

    const initialCounts = computeCounts(minT, maxT);
    const labels = initialCounts.map((_, i) => this._formatDuration(Math.round((edges[i] + edges[i + 1]) / 2)));
    const stripData = intervals.map((iv) => ({ value: [0, iv.start, iv.end] }));

    this._histogramRecompute = (winStart: number, winEnd: number) => {
      if (!this._chart) return;
      const counts = computeCounts(winStart, winEnd);
      this._chart.setOption({ series: [{}, { data: counts }] });
    };

    return {
      tooltip: {
        backgroundColor: "rgba(255,255,255,0.95)",
        borderColor: "#ddd",
        textStyle: { fontSize: 12, color: "#333" },
        formatter: (params: unknown) => {
          const p = params as { seriesIndex: number; dataIndex?: number; value: unknown };
          if (p.seriesIndex === 0) {
            const v = p.value as [number, number, number];
            return [
              `${new Date(v[1]).toLocaleString()}`,
              `${new Date(v[2]).toLocaleString()}`,
              `Duration: ${this._formatDuration(Math.max(0, v[2] - v[1]))}`,
            ].join("<br/>");
          }
          const i = p.dataIndex ?? 0;
          const lo = this._formatDuration(Math.round(edges[i]));
          const hi = this._formatDuration(Math.round(edges[i + 1]));
          return `${this._escapeHtml(lo)} – ${this._escapeHtml(hi)}<br/>Count: <b>${p.value}</b>`;
        },
      },
      axisPointer: { link: [{ xAxisIndex: [0] }] },
      grid: [
        { left: 48, right: 16, top: 12, height: 40 },
        { left: 48, right: 16, top: 110, bottom: 60 },
      ],
      xAxis: [
        {
          gridIndex: 0,
          type: "time",
          axisLine: { lineStyle: { color: "#ddd" } },
          axisLabel: { fontSize: 10, color: "#888" },
          splitLine: { show: false },
        },
        {
          gridIndex: 1,
          type: "category",
          data: labels,
          axisLine: { lineStyle: { color: "#ddd" } },
          axisLabel: { fontSize: 9, color: "#888", rotate: 45, interval: Math.floor(binCount / 10) },
        },
      ],
      yAxis: [
        {
          gridIndex: 0,
          type: "value",
          min: -1,
          max: 1,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        {
          gridIndex: 1,
          type: "value",
          name: "count",
          nameTextStyle: { fontSize: 10, color: "#888" },
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { fontSize: 10, color: "#888" },
          splitLine: { lineStyle: { color: "#f0f0f0" } },
        },
      ],
      dataZoom: [
        { type: "slider", xAxisIndex: 0, height: 16, top: 56, brushSelect: true },
        { type: "inside", xAxisIndex: 0 },
      ],
      series: [
        {
          type: "custom",
          xAxisIndex: 0,
          yAxisIndex: 0,
          renderItem: (
            _params: unknown,
            api: {
              value: (i: number) => number;
              coord: (p: number[]) => number[];
              size: (p: number[]) => number[];
              style: () => unknown;
            },
          ) => {
            const start = api.coord([api.value(1), 0]);
            const endPoint = api.coord([api.value(2), 0]);
            const stripHeight = (api.size([0, 2])[1] ?? 30) * 0.6;
            const width = Math.max(1, endPoint[0] - start[0]);
            return {
              type: "rect",
              shape: { x: start[0], y: start[1] - stripHeight / 2, width, height: stripHeight },
              style: { ...(api.style() as object), fill: "#728f67", opacity: 0.3 },
            };
          },
          encode: { x: [1, 2], y: 0 },
          data: stripData,
        },
        {
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: initialCounts,
          itemStyle: { color: "#728f67" },
          barCategoryGap: "10%",
        },
      ],
    };
  }

  _formatDuration(ms: number): string {
    if (ms < 1000) return `${ms} ms`;
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s} s`;
    const m = Math.round(s / 60);
    if (m < 60) return `${m} min`;
    const h = Math.floor(m / 60);
    const rem = m % 60;
    if (h < 24) return rem ? `${h}h ${rem}m` : `${h}h`;
    const d = Math.floor(h / 24);
    const remH = h % 24;
    return remH ? `${d}d ${remH}h` : `${d}d`;
  }

  _escapeHtml(s: string): string {
    return s.replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string,
    );
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
