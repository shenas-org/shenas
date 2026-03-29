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
 *       { key: "status", label: "Status", render: (row) => html`<status-dot ...>` },
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
    `,
  ];

  constructor() {
    super();
    this.columns = [];
    this.rows = [];
    this.rowClass = null;
    this.actions = null;
    this.emptyText = "No items";
  }

  render() {
    if (!this.rows || this.rows.length === 0) {
      return html`<p class="empty">${this.emptyText}</p>`;
    }

    const hasActions = typeof this.actions === "function";

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
    `;
  }
}

customElements.define("shenas-data-list", DataList);
