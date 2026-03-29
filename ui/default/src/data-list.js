import { LitElement, html, css } from "lit";
import { buttonStyles, tableStyles, utilityStyles } from "./shared-styles.js";

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

  static styles = [
    tableStyles,
    buttonStyles,
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
        color: #888;
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
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1px solid #ddd;
        background: #fff;
        color: #666;
        font-size: 1.1rem;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
      }
      .add-btn:hover {
        background: #f0f4ff;
        color: #0066cc;
        border-color: #0066cc;
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

  _onAdd() {
    this.dispatchEvent(new CustomEvent("add", { bubbles: true, composed: true }));
  }

  render() {
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
                  ? html`<td class="actions-cell">${this.actions(row)}</td>`
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
