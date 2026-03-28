import { tableFromIPC } from "apache-arrow";
import { LitElement, html, css } from "lit";

export class ShenasDataTable extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    pageSize: { type: Number, attribute: "page-size" },
    _tables: { state: true },
    _selectedTable: { state: true },
    _columns: { state: true },
    _data: { state: true },
    _sortCol: { state: true },
    _sortDesc: { state: true },
    _filters: { state: true },
    _page: { state: true },
    _colWidths: { state: true },
    _loading: { state: true },
    _error: { state: true },
  };

  static styles = css`
    :host {
      display: block;
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px 16px;
    }
    h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0 0 16px 0; }
    .controls { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
    select, input { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
    select { min-width: 200px; }
    .table-wrap { overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; table-layout: fixed; }
    th {
      position: relative;
      background: #f5f5f5;
      border-bottom: 2px solid #ddd;
      padding: 8px 12px;
      text-align: left;
      font-weight: 600;
      color: #333;
      white-space: nowrap;
      overflow: hidden;
      cursor: pointer;
      user-select: none;
    }
    th:hover { background: #eee; }
    .sort-indicator { margin-left: 4px; color: #999; }
    .resize-handle {
      position: absolute;
      right: 0; top: 0; bottom: 0;
      width: 4px;
      cursor: col-resize;
    }
    .resize-handle:hover { background: #4a90d9; }
    .filter-row th { padding: 4px 8px; background: #fafafa; border-bottom: 1px solid #eee; cursor: default; }
    .filter-row input { width: 100%; box-sizing: border-box; padding: 4px 6px; font-size: 12px; }
    td { padding: 6px 12px; border-bottom: 1px solid #f0f0f0; color: #444; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    tr:hover td { background: #f8f8ff; }
    .pagination { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: 13px; color: #666; }
    .pagination button { padding: 4px 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
    .pagination button:disabled { opacity: 0.4; cursor: default; }
    .pagination button:not(:disabled):hover { background: #f0f0f0; }
    .loading { color: #888; padding: 24px; text-align: center; }
    .error { color: #c00; background: #fee; padding: 12px; border-radius: 6px; }
    .page-info { flex: 1; text-align: center; }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this.pageSize = 25;
    this._tables = [];
    this._selectedTable = "";
    this._columns = [];
    this._data = [];
    this._sortCol = null;
    this._sortDesc = false;
    this._filters = {};
    this._page = 0;
    this._colWidths = {};
    this._loading = false;
    this._error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchTables();
  }

  async _fetchTables() {
    try {
      const res = await fetch(`${this.apiBase}/tables`);
      this._tables = await res.json();
      if (this._tables.length > 0) {
        this._selectedTable = `${this._tables[0].schema}.${this._tables[0].table}`;
        this._fetchData();
      }
    } catch (e) {
      this._error = e.message;
    }
  }

  async _fetchData() {
    this._loading = true;
    this._error = null;
    try {
      const sql = `SELECT * FROM ${this._selectedTable}`;
      const res = await fetch(`${this.apiBase}/query?sql=${encodeURIComponent(sql)}`);
      if (!res.ok) throw new Error(await res.text());
      const buf = await res.arrayBuffer();
      const table = tableFromIPC(buf);

      this._columns = table.schema.fields.map((f) => f.name);

      const rows = [];
      for (let i = 0; i < table.numRows; i++) {
        const row = {};
        for (const col of this._columns) {
          row[col] = table.getChild(col).get(i);
        }
        rows.push(row);
      }
      this._data = rows;
      this._page = 0;
      this._filters = {};
      this._sortCol = null;
    } catch (e) {
      this._error = e.message;
    }
    this._loading = false;
  }

  get _filteredData() {
    return this._data.filter((row) =>
      Object.entries(this._filters).every(([col, val]) => {
        if (!val) return true;
        const cell = row[col];
        return cell != null && String(cell).toLowerCase().includes(val.toLowerCase());
      })
    );
  }

  get _sortedData() {
    const data = [...this._filteredData];
    if (!this._sortCol) return data;
    const col = this._sortCol;
    const desc = this._sortDesc;
    return data.sort((a, b) => {
      const va = a[col], vb = b[col];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return desc ? 1 : -1;
      if (va > vb) return desc ? -1 : 1;
      return 0;
    });
  }

  get _pagedData() {
    const start = this._page * this.pageSize;
    return this._sortedData.slice(start, start + this.pageSize);
  }

  get _pageCount() {
    return Math.max(1, Math.ceil(this._sortedData.length / this.pageSize));
  }

  _onTableChange(e) {
    this._selectedTable = e.target.value;
    this._fetchData();
  }

  _onSort(col) {
    if (this._sortCol === col) {
      this._sortDesc = !this._sortDesc;
    } else {
      this._sortCol = col;
      this._sortDesc = false;
    }
  }

  _onFilter(col, value) {
    this._filters = { ...this._filters, [col]: value };
    this._page = 0;
  }

  _formatCell(value) {
    if (value == null) return "";
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    if (typeof value === "bigint") return value.toString();
    return String(value);
  }

  _onResizeStart(e, col) {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startWidth = this._colWidths[col] || 150;
    const onMove = (ev) => {
      this._colWidths = { ...this._colWidths, [col]: Math.max(50, startWidth + ev.clientX - startX) };
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  render() {
    if (this._error) return html`<div class="error">${this._error}</div>`;

    const tableSelector = html`
      <div class="controls">
        <h1>data table</h1>
        <select @change=${this._onTableChange}>
          ${this._tables.map(
            (t) => html`
              <option value="${t.schema}.${t.table}" ?selected=${`${t.schema}.${t.table}` === this._selectedTable}>
                ${t.schema}.${t.table}
              </option>
            `
          )}
        </select>
      </div>
    `;

    if (this._loading) return html`${tableSelector}<div class="loading">Loading...</div>`;
    if (this._data.length === 0) return html`${tableSelector}<div class="loading">No data</div>`;

    const rows = this._pagedData;

    return html`
      ${tableSelector}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${this._columns.map(
                (col) => html`
                  <th style="width:${this._colWidths[col] || 150}px" @click=${() => this._onSort(col)}>
                    ${col}
                    ${this._sortCol === col
                      ? html`<span class="sort-indicator">${this._sortDesc ? "v" : "^"}</span>`
                      : ""}
                    <div class="resize-handle" @mousedown=${(e) => this._onResizeStart(e, col)}></div>
                  </th>
                `
              )}
            </tr>
            <tr class="filter-row">
              ${this._columns.map(
                (col) => html`
                  <th>
                    <input
                      type="text"
                      placeholder="Filter..."
                      .value=${this._filters[col] || ""}
                      @input=${(e) => this._onFilter(col, e.target.value)}
                    />
                  </th>
                `
              )}
            </tr>
          </thead>
          <tbody>
            ${rows.map(
              (row) => html`
                <tr>
                  ${this._columns.map(
                    (col) => html`<td style="width:${this._colWidths[col] || 150}px">${this._formatCell(row[col])}</td>`
                  )}
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button ?disabled=${this._page === 0} @click=${() => this._page--}>Previous</button>
        <span class="page-info">
          Page ${this._page + 1} of ${this._pageCount}
          (${this._sortedData.length} rows)
        </span>
        <button ?disabled=${this._page >= this._pageCount - 1} @click=${() => this._page++}>Next</button>
      </div>
    `;
  }
}

customElements.define("shenas-data-table", ShenasDataTable);
