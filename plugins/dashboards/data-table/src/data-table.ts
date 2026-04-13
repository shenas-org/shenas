import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { gql, query as arrowQuery, arrowToRows } from "shenas-frontends";
import type { RowData } from "shenas-frontends";

interface TableInfo {
  schema: string;
  table: string;
}

interface ColMeta {
  dbType: string;
  description: string;
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

  static styles: CSSResult = css`
    :host {
      display: flex;
      flex-direction: column;
      font-family: system-ui, -apple-system, sans-serif;
      height: 100%;
      overflow: hidden;
    }
    h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0 0 12px 0; }
    .controls {
      display: flex; gap: 12px; align-items: center;
      margin-bottom: 12px; flex-wrap: wrap; flex-shrink: 0;
    }
    select, input {
      padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px;
    }
    select { min-width: 200px; }
    .compact-select { margin-bottom: 6px; font-size: 12px; padding: 3px 6px; }
    .table-wrap {
      overflow: auto; flex: 1;
      border: 1px solid #e0e0e0; border-radius: 4px; background: #fff;
    }
    table { border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; }
    th {
      position: relative; background: #f5f5f5; border-bottom: 1px solid #ddd;
      padding: 4px 8px; text-align: left; font-weight: 600; color: #555;
      white-space: nowrap; overflow: hidden; cursor: pointer; user-select: none;
      font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em;
    }
    th:hover { background: #eee; }
    .sort-indicator { margin-left: 3px; color: #999; }
    .resize-handle {
      position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize;
    }
    .resize-handle:hover { background: #4a90d9; }
    td {
      padding: 3px 8px; border-bottom: 1px solid #f0f0f0; color: #444;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    tr:hover td { background: #f8f8ff; }
    .pagination {
      display: flex; gap: 6px; align-items: center;
      padding: 4px 0; font-size: 11px; color: #888; flex-shrink: 0;
    }
    .pagination button {
      padding: 2px 8px; border: 1px solid #ddd; border-radius: 3px;
      background: #fff; cursor: pointer; font-size: 11px;
    }
    .pagination button:disabled { opacity: 0.4; cursor: default; }
    .pagination button:not(:disabled):hover { background: #f0f0f0; }
    .page-link.active { background: #728f67; color: #fff; border-color: #728f67; }
    .page-ellipsis { color: #aaa; font-size: 11px; padding: 0 2px; }
    .page-jump {
      width: 50px; padding: 2px 4px; font-size: 11px;
      border: 1px solid #ddd; border-radius: 3px; text-align: center;
    }
    .page-jump::-webkit-inner-spin-button { -webkit-appearance: none; }
    .loading { color: #888; padding: 24px; text-align: center; }
    .error { color: #c00; background: #fee; padding: 12px; border-radius: 6px; }
    .page-info { flex: 1; text-align: center; }
    .search-bar {
      display: flex; align-items: center; gap: 6px; padding: 4px 0; flex-shrink: 0;
    }
    .search-bar input {
      flex: 1; padding: 3px 8px; font-size: 12px;
      border: 1px solid #ddd; border-radius: 3px;
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

      // Fetch column type metadata from plugin Field declarations
      const [s, t] = this._selectedTable.split(".");
      const meta = await gql(
        this.apiBase,
        `query($s: String!, $t: String!) { tableColumnInfo(schema: $s, table: $t) { name dbType description unit nullable valueRange exampleValue interpretation } }`,
        { s, t },
      );
      this._colMeta = {};
      for (const c of (meta?.tableColumnInfo || []) as Array<ColMeta & { name: string }>) {
        this._colMeta[c.name] = c;
      }
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
    const term = this._searchTerm.toLowerCase();
    if (!term) return this._data;
    return this._data.filter((row) =>
      this._columns.some((col) => {
        const cell = row[col];
        return cell != null && String(cell).toLowerCase().includes(term);
      }),
    );
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
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${visibleCols.map(
                (col) => html`
                  <th style="width:${this._colWidths[col] || 120}px" title="${this._colTooltip(col)}" @click=${() => this._onSort(col)}>
                    ${col}
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
        <button ?disabled=${this._page >= this._pageCount - 1} @click=${() => (this._page = this._pageCount - 1)} title="Last">&raquo;</button>
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
        : html`<button
            class="page-link ${p === cur ? "active" : ""}"
            @click=${() => (this._page = p as number)}
          >
            ${(p as number) + 1}
          </button>`,
    )}`;
  }
}

customElements.define("shenas-data-table", ShenasDataTable);
