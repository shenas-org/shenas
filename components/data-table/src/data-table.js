import { tableFromIPC } from "apache-arrow";
import {
  createTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
} from "@tanstack/table-core";
import { LitElement, html, css } from "lit";

export class ShenasDataTable extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    pageSize: { type: Number, attribute: "page-size" },
    _tables: { state: true },
    _selectedTable: { state: true },
    _columns: { state: true },
    _data: { state: true },
    _sorting: { state: true },
    _columnFilters: { state: true },
    _pagination: { state: true },
    _columnSizing: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _resizing: { state: true },
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
      user-select: none;
    }
    th.sortable { cursor: pointer; }
    th.sortable:hover { background: #eee; }
    .sort-indicator { margin-left: 4px; color: #999; }
    .resize-handle {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      cursor: col-resize;
      background: transparent;
    }
    .resize-handle:hover, .resize-handle.active { background: #4a90d9; }
    .filter-row th { padding: 4px 8px; background: #fafafa; border-bottom: 1px solid #eee; }
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
    this._sorting = [];
    this._columnFilters = [];
    this._pagination = { pageIndex: 0, pageSize: 25 };
    this._columnSizing = {};
    this._loading = false;
    this._error = null;
    this._resizing = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._pagination = { pageIndex: 0, pageSize: this.pageSize };
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

      this._columns = table.schema.fields.map((f) => ({
        id: f.name,
        accessorKey: f.name,
        header: f.name,
        size: this._columnSizing[f.name] || 150,
      }));

      const rows = [];
      for (let i = 0; i < table.numRows; i++) {
        const row = {};
        for (const field of table.schema.fields) {
          const val = table.getChild(field.name).get(i);
          row[field.name] = val;
        }
        rows.push(row);
      }
      this._data = rows;
      this._pagination = { ...this._pagination, pageIndex: 0 };
    } catch (e) {
      this._error = e.message;
    }
    this._loading = false;
  }

  _getTable() {
    const self = this;
    return createTable({
      state: {
        sorting: this._sorting,
        columnFilters: this._columnFilters,
        pagination: this._pagination,
        columnSizing: this._columnSizing,
      },
      data: this._data,
      columns: this._columns,
      getCoreRowModel: getCoreRowModel(),
      getSortedRowModel: getSortedRowModel(),
      getFilteredRowModel: getFilteredRowModel(),
      getPaginationRowModel: getPaginationRowModel(),
      onSortingChange: (updater) => {
        self._sorting = typeof updater === "function" ? updater(self._sorting) : updater;
      },
      onColumnFiltersChange: (updater) => {
        self._columnFilters = typeof updater === "function" ? updater(self._columnFilters) : updater;
      },
      onPaginationChange: (updater) => {
        self._pagination = typeof updater === "function" ? updater(self._pagination) : updater;
      },
      onColumnSizingChange: (updater) => {
        self._columnSizing = typeof updater === "function" ? updater(self._columnSizing) : updater;
      },
      columnResizeMode: "onChange",
      enableColumnResizing: true,
    });
  }

  _onTableChange(e) {
    this._selectedTable = e.target.value;
    this._sorting = [];
    this._columnFilters = [];
    this._columnSizing = {};
    this._fetchData();
  }

  _formatCell(value) {
    if (value == null) return "";
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    if (typeof value === "bigint") return value.toString();
    return String(value);
  }

  _onResizeStart(e, headerId) {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = this._columnSizing[headerId] || 150;

    const onMove = (ev) => {
      const diff = ev.clientX - startX;
      this._columnSizing = { ...this._columnSizing, [headerId]: Math.max(50, startWidth + diff) };
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      this._resizing = null;
    };
    this._resizing = headerId;
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
              <option
                value="${t.schema}.${t.table}"
                ?selected=${`${t.schema}.${t.table}` === this._selectedTable}
              >
                ${t.schema}.${t.table}
              </option>
            `
          )}
        </select>
      </div>
    `;

    if (this._loading) return html`${tableSelector}<div class="loading">Loading...</div>`;
    if (this._data.length === 0) return html`${tableSelector}<div class="loading">No data</div>`;

    const table = this._getTable();
    const headerGroups = table.getHeaderGroups();
    const rows = table.getRowModel().rows;

    return html`
      ${tableSelector}
      <div class="table-wrap">
        <table>
          <thead>
            ${headerGroups.map(
              (hg) => html`
                <tr>
                  ${hg.headers.map(
                    (header) => html`
                      <th
                        class=${header.column.getCanSort() ? "sortable" : ""}
                        style="width: ${header.getSize()}px"
                        @click=${() => header.column.getCanSort() && header.column.toggleSorting()}
                      >
                        ${header.column.columnDef.header}
                        ${header.column.getIsSorted() === "asc"
                          ? html`<span class="sort-indicator">^</span>`
                          : header.column.getIsSorted() === "desc"
                            ? html`<span class="sort-indicator">v</span>`
                            : ""}
                        <div
                          class="resize-handle ${this._resizing === header.id ? "active" : ""}"
                          @mousedown=${(e) => this._onResizeStart(e, header.id)}
                        ></div>
                      </th>
                    `
                  )}
                </tr>
                <tr class="filter-row">
                  ${hg.headers.map(
                    (header) => html`
                      <th>
                        <input
                          type="text"
                          placeholder="Filter..."
                          .value=${header.column.getFilterValue() ?? ""}
                          @input=${(e) => header.column.setFilterValue(e.target.value || undefined)}
                        />
                      </th>
                    `
                  )}
                </tr>
              `
            )}
          </thead>
          <tbody>
            ${rows.map(
              (row) => html`
                <tr>
                  ${row.getVisibleCells().map(
                    (cell) => html`<td style="width: ${cell.column.getSize()}px">${this._formatCell(cell.getValue())}</td>`
                  )}
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button ?disabled=${!table.getCanPreviousPage()} @click=${() => table.previousPage()}>Previous</button>
        <span class="page-info">
          Page ${table.getState().pagination.pageIndex + 1} of ${table.getPageCount()}
          (${table.getFilteredRowModel().rows.length} rows)
        </span>
        <button ?disabled=${!table.getCanNextPage()} @click=${() => table.nextPage()}>Next</button>
      </div>
    `;
  }
}

customElements.define("shenas-data-table", ShenasDataTable);
