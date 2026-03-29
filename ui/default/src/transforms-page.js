import { LitElement, html, css } from "lit";

class TransformsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _transforms: { state: true },
    _loading: { state: true },
    _editing: { state: true },
    _editSql: { state: true },
    _message: { state: true },
    _previewRows: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th {
      text-align: left;
      padding: 0.4rem 0.6rem;
      color: #666;
      font-weight: 500;
      border-bottom: 1px solid #e0e0e0;
    }
    td {
      padding: 0.4rem 0.6rem;
      border-bottom: 1px solid #f0f0f0;
    }
    .id {
      color: #888;
      width: 40px;
    }
    .mapping {
      font-family: monospace;
      font-size: 0.85rem;
    }
    .desc {
      color: #555;
    }
    .status {
      font-size: 0.85rem;
    }
    .actions {
      white-space: nowrap;
    }
    button {
      padding: 0.3rem 0.6rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.8rem;
      margin-left: 0.3rem;
    }
    button:hover {
      background: #f5f5f5;
    }
    button.danger {
      color: #c00;
      border-color: #e8c0c0;
    }
    .default-badge {
      font-size: 0.75rem;
      color: #888;
      background: #f0f0f0;
      padding: 1px 5px;
      border-radius: 3px;
      margin-left: 4px;
    }
    .edit-panel {
      margin: 1rem 0;
      padding: 1rem;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      background: #fafafa;
    }
    .edit-panel h3 {
      margin: 0 0 0.8rem;
      font-size: 1rem;
    }
    textarea {
      width: 100%;
      min-height: 120px;
      font-family: monospace;
      font-size: 0.85rem;
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      resize: vertical;
      box-sizing: border-box;
    }
    .edit-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.8rem;
    }
    .preview-table {
      margin-top: 1rem;
      max-height: 300px;
      overflow: auto;
    }
    .preview-table table {
      font-size: 0.8rem;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-bottom: 1rem;
      font-size: 0.85rem;
    }
    .message.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .message.error {
      background: #fce4ec;
      color: #c62828;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
    .disabled-row {
      opacity: 0.5;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._transforms = [];
    this._loading = true;
    this._editing = null;
    this._editSql = "";
    this._message = null;
    this._previewRows = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll() {
    this._loading = true;
    const resp = await fetch(`${this.apiBase}/transforms`);
    this._transforms = resp.ok ? await resp.json() : [];
    this._loading = false;
  }

  async _toggle(t) {
    const action = t.enabled ? "disable" : "enable";
    await fetch(`${this.apiBase}/transforms/${t.id}/${action}`, {
      method: "POST",
    });
    await this._fetchAll();
  }

  async _delete(t) {
    const resp = await fetch(`${this.apiBase}/transforms/${t.id}`, {
      method: "DELETE",
    });
    const data = await resp.json();
    if (data.ok) {
      this._message = { type: "success", text: data.message };
      await this._fetchAll();
    } else {
      this._message = {
        type: "error",
        text: data.detail || data.message || "Delete failed",
      };
    }
  }

  _startEdit(t) {
    this._editing = t.id;
    this._editSql = t.sql;
    this._previewRows = null;
  }

  _cancelEdit() {
    this._editing = null;
    this._editSql = "";
    this._previewRows = null;
  }

  async _saveEdit() {
    const resp = await fetch(`${this.apiBase}/transforms/${this._editing}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql: this._editSql }),
    });
    if (resp.ok) {
      this._message = { type: "success", text: "Transform updated" };
      this._editing = null;
      await this._fetchAll();
    } else {
      const data = await resp.json();
      this._message = { type: "error", text: data.detail || "Update failed" };
    }
  }

  async _preview() {
    const resp = await fetch(
      `${this.apiBase}/transforms/${this._editing}/test?limit=5`,
      { method: "POST" },
    );
    if (resp.ok) {
      this._previewRows = await resp.json();
    } else {
      const data = await resp.json();
      this._message = {
        type: "error",
        text: data.detail || "Preview failed",
      };
    }
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading transforms...</p>`;
    }

    return html`
      ${this._message
        ? html`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`
        : ""}
      ${this._editing ? this._renderEditor() : ""}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Source</th>
            <th>Target</th>
            <th>Description</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._transforms.map(
            (t) => html`
              <tr class="${t.enabled ? "" : "disabled-row"}">
                <td class="id">${t.id}</td>
                <td class="mapping">
                  ${t.source_duckdb_schema}.${t.source_duckdb_table}
                </td>
                <td class="mapping">
                  ${t.target_duckdb_schema}.${t.target_duckdb_table}
                </td>
                <td class="desc">
                  ${t.description || ""}
                  ${t.is_default
                    ? html`<span class="default-badge">default</span>`
                    : ""}
                </td>
                <td class="status">
                  ${t.enabled ? "enabled" : "disabled"}
                </td>
                <td class="actions">
                  <button @click=${() => this._startEdit(t)}>Edit</button>
                  <button @click=${() => this._toggle(t)}>
                    ${t.enabled ? "Disable" : "Enable"}
                  </button>
                  ${!t.is_default
                    ? html`<button
                        class="danger"
                        @click=${() => this._delete(t)}
                      >
                        Delete
                      </button>`
                    : ""}
                </td>
              </tr>
            `,
          )}
        </tbody>
      </table>
    `;
  }

  _renderEditor() {
    const t = this._transforms.find((x) => x.id === this._editing);
    if (!t) return "";
    return html`
      <div class="edit-panel">
        <h3>
          Edit: ${t.source_duckdb_schema}.${t.source_duckdb_table} ->
          ${t.target_duckdb_schema}.${t.target_duckdb_table}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${(e) => (this._editSql = e.target.value)}
        ></textarea>
        <div class="edit-actions">
          <button @click=${this._saveEdit}>Save</button>
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>Cancel</button>
        </div>
        ${this._previewRows ? this._renderPreview() : ""}
      </div>
    `;
  }

  _renderPreview() {
    if (!this._previewRows || this._previewRows.length === 0) {
      return html`<p class="loading">No preview rows</p>`;
    }
    const cols = Object.keys(this._previewRows[0]);
    return html`
      <div class="preview-table">
        <table>
          <thead>
            <tr>
              ${cols.map((c) => html`<th>${c}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this._previewRows.map(
              (row) => html`
                <tr>
                  ${cols.map((c) => html`<td>${row[c]}</td>`)}
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>
    `;
  }
}

customElements.define("shenas-transforms", TransformsPage);
