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
      .add-row {
        display: flex;
        justify-content: flex-end;
        margin-top: 0.5rem;
      }
      .add-btn {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: 2px solid var(--shenas-primary, #0066cc);
        background: var(--shenas-bg, #fff);
        color: var(--shenas-primary, #0066cc);
        font-size: 1.2rem;
        font-weight: 600;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition: background 0.15s, color 0.15s;
      }
      .add-btn:hover {
        background: var(--shenas-primary, #0066cc);
        color: var(--shenas-bg, #fff);
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
    const addRow = this.showAdd
      ? html`<div class="add-row"><button class="add-btn" title="Add" @click=${this._onAdd}>+</button></div>`
      : "";

    if (!this.rows || this.rows.length === 0) {
      return html`<p class="empty">${this.emptyText}</p>${addRow}`;
    }

    return html`
      <table>
        <thead>
          <tr>
            ${this.columns.map((col) => html`<th>${col.label}</th>`)}
            ${hasActions ? html`<th></th>` : ""}
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(
            (row) => html`
              <tr class="${this.rowClass ? this.rowClass(row) : ""}">
                ${this.columns.map((col) => html`
                  <td class="${col.class || ""}">
                    ${col.render ? col.render(row) : row[col.key]}
                  </td>
                `)}
                ${hasActions
                  ? html`<td class="actions-cell">${this.actions!(row)}</td>`
                  : ""}
              </tr>
            `,
          )}
        </tbody>
      </table>
      ${addRow}
    `;
  }
}

customElements.define("shenas-data-list", DataList);
