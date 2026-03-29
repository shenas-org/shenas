import { LitElement, html, css } from "lit";
import { buttonStyles, messageStyles, tableStyles, utilityStyles } from "./shared-styles.js";

const _inspectBtnStyle = "background:none;border:none;cursor:pointer;color:#bbb;font-size:0.7rem;padding:0 2px";

class TransformsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    source: { type: String },
    _transforms: { state: true },
    _loading: { state: true },
    _editing: { state: true },
    _editSql: { state: true },
    _message: { state: true },
    _previewRows: { state: true },
    _creating: { state: true },
    _newForm: { state: true },
    _dbTables: { state: true },
    _schemaTables: { state: true },
  };

  static styles = [
    tableStyles,
    buttonStyles,
    messageStyles,
    utilityStyles,
    css`
      :host {
        display: block;
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
      textarea.readonly {
        background: #f5f5f5;
        color: #666;
        cursor: default;
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
      .disabled-row {
        opacity: 0.5;
      }
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        margin-bottom: 0.8rem;
      }
      .form-grid label {
        font-size: 0.8rem;
        color: #666;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-grid input,
      .form-grid select {
        padding: 0.35rem 0.5rem;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
      }
      .form-full {
        grid-column: 1 / -1;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.source = "";
    this._transforms = [];
    this._loading = true;
    this._editing = null;
    this._editSql = "";
    this._message = null;
    this._previewRows = null;
    this._creating = false;
    this._newForm = this._emptyForm();
    this._dbTables = {};
    this._schemaTables = {};
  }

  _emptyForm() {
    return {
      source_duckdb_table: "",
      target_duckdb_table: "",
      description: "",
      sql: "",
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll() {
    this._loading = true;
    const params = this.source ? `?source=${this.source}` : "";
    const resp = await fetch(`${this.apiBase}/transforms${params}`);
    this._transforms = resp.ok ? await resp.json() : [];
    this._loading = false;
  }

  _inspectTable(schema, table) {
    this.dispatchEvent(new CustomEvent("inspect-table", {
      bubbles: true,
      composed: true,
      detail: { schema, table },
    }));
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

  async _startCreate() {
    this._creating = true;
    this._newForm = this._emptyForm();
    this._editing = null;
    this._previewRows = null;
    const [tablesResp, schemaTablesResp] = await Promise.all([
      fetch(`${this.apiBase}/db/tables`),
      fetch(`${this.apiBase}/db/schema-tables`),
    ]);
    this._dbTables = tablesResp.ok ? await tablesResp.json() : {};
    this._schemaTables = schemaTablesResp.ok ? await schemaTablesResp.json() : {};
  }

  _cancelCreate() {
    this._creating = false;
    this._newForm = this._emptyForm();
  }

  _updateNewForm(field, value) {
    this._newForm = { ...this._newForm, [field]: value };
  }

  async _saveCreate() {
    const f = this._newForm;
    if (!f.source_duckdb_table || !f.target_duckdb_table || !f.sql) {
      this._message = { type: "error", text: "Fill in all required fields" };
      return;
    }
    const resp = await fetch(`${this.apiBase}/transforms`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_duckdb_schema: this.source,
        source_duckdb_table: f.source_duckdb_table,
        target_duckdb_schema: "metrics",
        target_duckdb_table: f.target_duckdb_table,
        source_plugin: this.source,
        description: f.description,
        sql: f.sql,
      }),
    });
    if (resp.ok) {
      this._message = { type: "success", text: "Transform created" };
      this._creating = false;
      this._newForm = this._emptyForm();
      await this._fetchAll();
    } else {
      const data = await resp.json();
      this._message = { type: "error", text: data.detail || "Create failed" };
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
      ${this._creating ? this._renderCreateForm() : ""}
      <shenas-data-list
        ?show-add=${!this._creating && !this._editing}
        @add=${this._startCreate}
        .columns=${[
          { key: "id", label: "ID", class: "muted" },
          { label: "Source", class: "mono", render: (t) => html`${t.source_duckdb_schema}.${t.source_duckdb_table} <button style=${_inspectBtnStyle} title="Inspect table" @click=${() => this._inspectTable(t.source_duckdb_schema, t.source_duckdb_table)}>&#9655;</button>` },
          { label: "Target", class: "mono", render: (t) => html`${t.target_duckdb_schema}.${t.target_duckdb_table} <button style=${_inspectBtnStyle} title="Inspect table" @click=${() => this._inspectTable(t.target_duckdb_schema, t.target_duckdb_table)}>&#9655;</button>` },
          { label: "Description", render: (t) => html`${t.description || ""}${t.is_default ? html`<span style="font-size:0.75rem;color:#888;background:#f0f0f0;padding:1px 5px;border-radius:3px;margin-left:4px">default</span>` : ""}` },
          { label: "Status", render: (t) => html`<status-toggle ?enabled=${t.enabled} toggleable @toggle=${() => this._toggle(t)}></status-toggle>` },
        ]}
        .rows=${this._transforms}
        .rowClass=${(t) => t.enabled ? "" : "disabled-row"}
        .actions=${(t) => html`
          ${!t.is_default
            ? html`<button @click=${() => this._startEdit(t)}>Edit</button>`
            : html`<button @click=${() => this._startEdit(t)}>View</button>`}
          ${!t.is_default
            ? html`<button class="danger" @click=${() => this._delete(t)}>Delete</button>`
            : ""}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
    `;
  }

  _renderCreateForm() {
    const f = this._newForm;
    const pipe = this.source;
    const sourceTables = this._dbTables[pipe] || [];
    const allSchemaTables = Object.values(this._schemaTables || {}).flat();
    return html`
      <shenas-form-panel
        title="New transform"
        submit-label="Create"
        @submit=${this._saveCreate}
        @cancel=${this._cancelCreate}
      >
        <div class="form-grid">
          <label>
            Pipe table
            <select
              .value=${f.source_duckdb_table}
              @change=${(e) => this._updateNewForm("source_duckdb_table", e.target.value)}
            >
              <option value="">-- select --</option>
              ${sourceTables.map((t) => html`<option value=${t} ?selected=${f.source_duckdb_table === t}>${t}</option>`)}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${f.target_duckdb_table}
              @change=${(e) => this._updateNewForm("target_duckdb_table", e.target.value)}
            >
              <option value="">-- select --</option>
              ${allSchemaTables.map((t) => html`<option value=${t} ?selected=${f.target_duckdb_table === t}>${t}</option>`)}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${f.description}
              @input=${(e) => this._updateNewForm("description", e.target.value)}
            />
          </label>
        </div>
        <textarea
          .value=${f.sql}
          @input=${(e) => this._updateNewForm("sql", e.target.value)}
          placeholder="SELECT ... FROM ${pipe}.${f.source_duckdb_table || "table_name"}"
        ></textarea>
      </shenas-form-panel>
    `;
  }

  _renderEditor() {
    const t = this._transforms.find((x) => x.id === this._editing);
    if (!t) return "";
    const readonly = t.is_default;
    return html`
      <div class="edit-panel">
        <h3>
          ${readonly ? "View" : "Edit"}: ${t.source_duckdb_schema}.${t.source_duckdb_table} ->
          ${t.target_duckdb_schema}.${t.target_duckdb_table}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${(e) => (this._editSql = e.target.value)}
          ?readonly=${readonly}
          class="${readonly ? "readonly" : ""}"
        ></textarea>
        <div class="edit-actions">
          ${!readonly
            ? html`<button @click=${this._saveEdit}>Save</button>`
            : ""}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${readonly ? "Close" : "Cancel"}</button>
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
