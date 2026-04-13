import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResultGroup } from "lit";
import { buttonStyles, linkStyles, tableStyles, utilityStyles } from "./shared-styles.ts";

type Row = Record<string, unknown>;

export interface DataListColumn {
  key: string;
  label: string;
  class?: string;
  render?: (row: Row) => unknown;
}

/**
 * Generic data list table.
 *
 * Usage:
 *   <shenas-data-list
 *     .columns=${[
 *       { key: "name", label: "Name" },
 *       { key: "version", label: "Version", class: "mono" },
 *       { key: "status", label: "Status", render: (row) => html`<status-toggle ...>` },
 *     ]}
 *     .rows=${items}
 *     .rowClass=${(row) => row.enabled ? "" : "disabled-row"}
 *     .actions=${(row) => html`<button @click=${() => edit(row)}>Edit</button>`}
 *     emptyText="No items"
 *   ></shenas-data-list>
 */
class DataList extends LitElement {
  static properties = {
    columns: { type: Array },
    rows: { type: Array },
    rowClass: { type: Object },
    actions: { type: Object },
    emptyText: { type: String, attribute: "empty-text" },
    showAdd: { type: Boolean, attribute: "show-add" },
  };

  declare columns: DataListColumn[];
  declare rows: Row[];
  declare rowClass: ((row: Row) => string) | null;
  declare actions: ((row: Row) => unknown) | null;
  declare emptyText: string;
  declare showAdd: boolean;

  static styles: CSSResultGroup = [
    tableStyles,
    buttonStyles,
    linkStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .mono {
        font-family: monospace;
        font-size: 0.85rem;
      }
      .muted {
        color: var(--shenas-text-muted, #888);
      }
      .actions-cell {
        white-space: nowrap;
      }
      .disabled-row {
        opacity: 0.5;
      }
      .top-bar {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 0.5rem;
      }
      .add-btn {
        padding: 0.35rem 0.8rem;
        border-radius: 4px;
        border: 1px solid var(--shenas-border, #ccc);
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
        font-size: 0.85rem;
        cursor: pointer;
        transition:
          background 0.15s,
          border-color 0.15s;
      }
      .add-btn:hover {
        background: var(--shenas-bg-secondary, #f5f5f5);
        border-color: var(--shenas-text-muted, #888);
      }
    `,
  ];

  constructor() {
    super();
    this.columns = [];
    this.rows = [];
    this.rowClass = null;
    this.actions = null;
    this.emptyText = "No items";
    this.showAdd = false;
  }

  _onAdd(): void {
    this.dispatchEvent(new CustomEvent("add", { bubbles: true, composed: true }));
  }

  render(): TemplateResult | unknown {
    const hasActions = typeof this.actions === "function";
    const topBar = this.showAdd
      ? html`<div class="top-bar"><button class="add-btn" @click=${this._onAdd}>Add</button></div>`
      : "";

    if (!this.rows || this.rows.length === 0) {
      return html`${topBar}
        <p class="empty">${this.emptyText}</p>`;
    }

    return html`
      ${topBar}
      <table>
        <thead>
          <tr>
            ${this.columns.map((col) => html`<th>${col.label}</th>`)} ${hasActions ? html`<th></th>` : ""}
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(
            (row) => html`
              <tr class="${this.rowClass ? this.rowClass(row) : ""}">
                ${this.columns.map(
                  (col) => html` <td class="${col.class || ""}">${col.render ? col.render(row) : row[col.key]}</td> `,
                )}
                ${hasActions ? html`<td class="actions-cell">${this.actions!(row)}</td>` : ""}
              </tr>
            `,
          )}
        </tbody>
      </table>
    `;
  }
}

customElements.define("shenas-data-list", DataList);
