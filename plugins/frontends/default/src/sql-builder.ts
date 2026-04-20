/**
 * <sql-builder> -- visual SELECT query builder for non-technical users.
 *
 * Renders column picker, filter rows, order-by, and limit controls.
 * Emits structured SelectQuery objects via @change events.
 * The backend generates the actual SQL from these objects.
 */
import { LitElement, html, css } from "lit";
import { buttonStyles, formStyles } from "shenas-frontends";

interface SelectColumn {
  name: string;
  alias: string | null;
  aggregate: string | null;
}

interface Filter {
  column: string;
  operator: string;
  value: string | null;
}

interface OrderByEntry {
  column: string;
  direction: string;
}

interface SelectQuery {
  columns: SelectColumn[];
  filters: Filter[];
  group_by: string[];
  order_by: OrderByEntry[];
  limit: number | null;
}

const OPERATORS: Record<string, string> = {
  eq: "equals",
  neq: "not equals",
  gt: ">",
  lt: "<",
  gte: ">=",
  lte: "<=",
  contains: "contains",
  starts_with: "starts with",
  is_null: "is empty",
  is_not_null: "is not empty",
};

const NULLARY_OPERATORS = new Set(["is_null", "is_not_null"]);

const AGGREGATES: Record<string, string> = {
  "": "none",
  sum: "SUM",
  avg: "AVG",
  count: "COUNT",
  min: "MIN",
  max: "MAX",
};

class SqlBuilder extends LitElement {
  static properties = {
    columns: { type: Array },
    value: { type: Object },
    _showAdvanced: { state: true },
  };

  static styles = [
    buttonStyles,
    formStyles,
    css`
      :host {
        display: block;
        font-size: 0.85rem;
      }

      /* -- Columns -- */
      .col-grid {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 0.2rem 0.6rem;
        align-items: center;
        margin-bottom: 0.8rem;
      }
      .col-grid input[type="checkbox"] {
        margin: 0;
      }
      .col-grid input[type="text"] {
        padding: 0.2rem 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.8rem;
        width: 100px;
      }

      /* -- Filters -- */
      .filter-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        margin-bottom: 0.3rem;
      }
      .filter-row select,
      .filter-row input {
        padding: 0.25rem 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.8rem;
      }
      .filter-row input[type="text"] {
        flex: 1;
        min-width: 80px;
      }

      /* -- Sections -- */
      .section-label {
        font-weight: 600;
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        margin: 0.6rem 0 0.3rem;
      }

      .advanced-toggle {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        cursor: pointer;
        border: none;
        background: none;
        padding: 0;
        text-decoration: underline;
        margin-top: 0.4rem;
      }

      .order-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        margin-bottom: 0.3rem;
      }
      .order-row select {
        padding: 0.25rem 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.8rem;
      }

      .limit-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
      }
      .limit-row input {
        width: 80px;
        padding: 0.25rem 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.8rem;
      }

      .remove-btn {
        background: none;
        border: none;
        color: #c00;
        cursor: pointer;
        font-size: 0.85rem;
        padding: 0 0.3rem;
      }
    `,
  ];

  declare columns: string[];
  declare value: SelectQuery;
  declare _showAdvanced: boolean;

  constructor() {
    super();
    this.columns = [];
    this.value = { columns: [], filters: [], group_by: [], order_by: [], limit: null };
    this._showAdvanced = false;
  }

  private _emit(): void {
    this.dispatchEvent(new CustomEvent("change", { detail: this.value, bubbles: true, composed: true }));
  }

  // -- Column management --

  private _isColumnSelected(name: string): boolean {
    return this.value.columns.some((c) => c.name === name);
  }

  private _toggleColumn(name: string, checked: boolean): void {
    const columns = checked
      ? [...this.value.columns, { name, alias: null, aggregate: null }]
      : this.value.columns.filter((c) => c.name !== name);
    this.value = { ...this.value, columns };
    this._emit();
  }

  private _selectAll(): void {
    this.value = {
      ...this.value,
      columns: this.columns.map((name) => {
        const existing = this.value.columns.find((c) => c.name === name);
        return existing || { name, alias: null, aggregate: null };
      }),
    };
    this._emit();
  }

  private _selectNone(): void {
    this.value = { ...this.value, columns: [] };
    this._emit();
  }

  private _setAlias(name: string, alias: string): void {
    this.value = {
      ...this.value,
      columns: this.value.columns.map((c) => (c.name === name ? { ...c, alias: alias || null } : c)),
    };
    this._emit();
  }

  private _setAggregate(name: string, aggregate: string): void {
    this.value = {
      ...this.value,
      columns: this.value.columns.map((c) => (c.name === name ? { ...c, aggregate: aggregate || null } : c)),
    };
    this._emit();
  }

  // -- Filter management --

  private _addFilter(): void {
    const column = this.columns[0] || "";
    this.value = {
      ...this.value,
      filters: [...this.value.filters, { column, operator: "eq", value: "" }],
    };
    this._emit();
  }

  private _updateFilter(index: number, field: keyof Filter, val: string): void {
    const filters = [...this.value.filters];
    filters[index] = { ...filters[index], [field]: val };
    if (NULLARY_OPERATORS.has(filters[index].operator)) {
      filters[index].value = null;
    }
    this.value = { ...this.value, filters };
    this._emit();
  }

  private _removeFilter(index: number): void {
    const filters = [...this.value.filters];
    filters.splice(index, 1);
    this.value = { ...this.value, filters };
    this._emit();
  }

  // -- Order by management --

  private _addOrderBy(): void {
    const column = this.columns[0] || "";
    this.value = {
      ...this.value,
      order_by: [...this.value.order_by, { column, direction: "asc" }],
    };
    this._emit();
  }

  private _updateOrderBy(index: number, field: keyof OrderByEntry, val: string): void {
    const order_by = [...this.value.order_by];
    order_by[index] = { ...order_by[index], [field]: val };
    this.value = { ...this.value, order_by };
    this._emit();
  }

  private _removeOrderBy(index: number): void {
    const order_by = [...this.value.order_by];
    order_by.splice(index, 1);
    this.value = { ...this.value, order_by };
    this._emit();
  }

  // -- Limit --

  private _setLimit(val: string): void {
    this.value = { ...this.value, limit: val ? parseInt(val, 10) : null };
    this._emit();
  }

  // -- Rendering --

  render() {
    const availableCols = this.columns.filter((c) => !c.startsWith("_dlt_"));
    const selectedCount = this.value.columns.length;

    return html`
      <div class="section-label">
        Columns (${selectedCount}/${availableCols.length})
        <span style="margin-left:0.5rem">
          <a
            href="#"
            @click=${(e: Event) => {
              e.preventDefault();
              this._selectAll();
            }}
            style="font-size:0.75rem"
            >all</a
          >
          /
          <a
            href="#"
            @click=${(e: Event) => {
              e.preventDefault();
              this._selectNone();
            }}
            style="font-size:0.75rem"
            >none</a
          >
        </span>
      </div>
      <div class="col-grid">
        ${availableCols.map((col) => {
          const selected = this._isColumnSelected(col);
          const entry = this.value.columns.find((c) => c.name === col);
          return html`
            <input
              type="checkbox"
              ?checked=${selected}
              @change=${(e: Event) => this._toggleColumn(col, (e.target as HTMLInputElement).checked)}
            />
            <span>${col}</span>
            <span>
              ${selected
                ? html`<input
                    type="text"
                    placeholder="alias"
                    .value=${entry?.alias || ""}
                    @input=${(e: InputEvent) => this._setAlias(col, (e.target as HTMLInputElement).value)}
                  />`
                : ""}
            </span>
          `;
        })}
      </div>

      <div class="section-label">
        Filters
        <button
          @click=${this._addFilter}
          style="margin-left:0.5rem;font-size:0.75rem;padding:0.1rem 0.4rem;border:1px solid #ccc;border-radius:3px;background:#fff;cursor:pointer"
        >
          + Add
        </button>
      </div>
      ${this.value.filters.map(
        (filter, idx) => html`
          <div class="filter-row">
            <select @change=${(e: Event) => this._updateFilter(idx, "column", (e.target as HTMLSelectElement).value)}>
              ${availableCols.map((c) => html`<option value=${c} ?selected=${filter.column === c}>${c}</option>`)}
            </select>
            <select @change=${(e: Event) => this._updateFilter(idx, "operator", (e.target as HTMLSelectElement).value)}>
              ${Object.entries(OPERATORS).map(
                ([k, label]) => html`<option value=${k} ?selected=${filter.operator === k}>${label}</option>`,
              )}
            </select>
            ${!NULLARY_OPERATORS.has(filter.operator)
              ? html`<input
                  type="text"
                  .value=${filter.value || ""}
                  placeholder="value"
                  @input=${(e: InputEvent) => this._updateFilter(idx, "value", (e.target as HTMLInputElement).value)}
                />`
              : ""}
            <button class="remove-btn" @click=${() => this._removeFilter(idx)}>x</button>
          </div>
        `,
      )}

      <button class="advanced-toggle" @click=${() => (this._showAdvanced = !this._showAdvanced)}>
        ${this._showAdvanced ? "Hide" : "Show"} advanced (aggregate, order, limit)
      </button>

      ${this._showAdvanced
        ? html`
            <div class="section-label">Aggregate</div>
            ${this.value.columns.length > 0
              ? html`<div class="col-grid" style="grid-template-columns: 1fr auto">
                  ${this.value.columns.map(
                    (col) => html`
                      <span>${col.alias || col.name}</span>
                      <select
                        @change=${(e: Event) => this._setAggregate(col.name, (e.target as HTMLSelectElement).value)}
                      >
                        ${Object.entries(AGGREGATES).map(
                          ([k, label]) =>
                            html`<option value=${k} ?selected=${(col.aggregate || "") === k}>${label}</option>`,
                        )}
                      </select>
                    `,
                  )}
                </div>`
              : html`<div style="font-size:0.8rem;color:#888">Select columns first</div>`}

            <div class="section-label">
              Order by
              <button
                @click=${this._addOrderBy}
                style="margin-left:0.5rem;font-size:0.75rem;padding:0.1rem 0.4rem;border:1px solid #ccc;border-radius:3px;background:#fff;cursor:pointer"
              >
                + Add
              </button>
            </div>
            ${this.value.order_by.map(
              (ob, idx) => html`
                <div class="order-row">
                  <select
                    @change=${(e: Event) => this._updateOrderBy(idx, "column", (e.target as HTMLSelectElement).value)}
                  >
                    ${availableCols.map((c) => html`<option value=${c} ?selected=${ob.column === c}>${c}</option>`)}
                  </select>
                  <select
                    @change=${(e: Event) =>
                      this._updateOrderBy(idx, "direction", (e.target as HTMLSelectElement).value)}
                  >
                    <option value="asc" ?selected=${ob.direction === "asc"}>ASC</option>
                    <option value="desc" ?selected=${ob.direction === "desc"}>DESC</option>
                  </select>
                  <button class="remove-btn" @click=${() => this._removeOrderBy(idx)}>x</button>
                </div>
              `,
            )}

            <div class="section-label">Limit</div>
            <div class="limit-row">
              <input
                type="number"
                min="1"
                placeholder="no limit"
                .value=${this.value.limit?.toString() || ""}
                @input=${(e: InputEvent) => this._setLimit((e.target as HTMLInputElement).value)}
              />
            </div>
          `
        : ""}
    `;
  }
}

customElements.define("sql-builder", SqlBuilder);
