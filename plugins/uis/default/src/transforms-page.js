import { LitElement, html, css } from "lit";
import { gql, gqlFull, registerCommands, renderMessage } from "./api.js";
import { buttonStyles, formStyles, messageStyles, tableStyles } from "./shared-styles.js";

const _inspectBtnStyle = "background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";

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
    formStyles,
    messageStyles,
    css`
      :host {
        display: block;
      }
      .edit-panel {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
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
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        resize: vertical;
        box-sizing: border-box;
      }
      textarea.readonly {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text-secondary, #666);
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
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      .form-grid input,
      .form-grid select {
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
    const data = await gql(this.apiBase, `query($source: String) { transforms(source: $source) { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description sql isDefault enabled } }`, { source: this.source || null });
    this._transforms = data?.transforms || [];
    this._loading = false;
    this._registerCommands();
  }

  _registerCommands() {
    const commands = [];
    for (const t of this._transforms) {
      const desc = t.description || `${t.sourceDuckdbTable} -> ${t.targetDuckdbTable}`;
      commands.push({
        id: `transform:toggle:${t.id}`,
        category: "Transform",
        label: `${t.enabled ? "Disable" : "Enable"} #${t.id}`,
        description: desc,
        action: () => this._toggle(t),
      });
      if (!t.isDefault) {
        commands.push({
          id: `transform:delete:${t.id}`,
          category: "Transform",
          label: `Delete #${t.id}`,
          description: desc,
          action: () => this._delete(t),
        });
      }
    }
    registerCommands(this, `transforms:${this.source}`, commands);
  }


  _inspectTable(schema, table) {
    this.dispatchEvent(new CustomEvent("inspect-table", {
      bubbles: true,
      composed: true,
      detail: { schema, table },
    }));
  }

  async _toggle(t) {
    const mutation = t.enabled
      ? `mutation($id: Int!) { disableTransform(transformId: $id) { id enabled } }`
      : `mutation($id: Int!) { enableTransform(transformId: $id) { id enabled } }`;
    await gqlFull(this.apiBase, mutation, { id: t.id });
    await this._fetchAll();
  }

  async _delete(t) {
    const { ok, data } = await gqlFull(this.apiBase, `mutation($id: Int!) { deleteTransform(transformId: $id) { ok message } }`, { id: t.id });
    if (ok && data?.deleteTransform?.ok) {
      this._message = { type: "success", text: `Deleted transform #${t.id}` };
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Delete failed" };
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
    const { ok } = await gqlFull(this.apiBase, `mutation($id: Int!, $sql: String!) { updateTransform(transformId: $id, sql: $sql) { id } }`, { id: this._editing, sql: this._editSql });
    if (ok) {
      this._message = { type: "success", text: "Transform updated" };
      this._editing = null;
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Update failed" };
    }
  }

  async _startCreate() {
    this._creating = true;
    this._newForm = this._emptyForm();
    this._editing = null;
    this._previewRows = null;
    const data = await gql(this.apiBase, `{ dbTables schemaTables }`);
    this._dbTables = data?.dbTables || {};
    this._schemaTables = data?.schemaTables || {};
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
    const { ok, data } = await gqlFull(this.apiBase, `mutation($input: TransformCreateInput!) { createTransform(transformInput: $input) { id } }`, {
      input: {
        sourceDuckdbSchema: this.source,
        sourceDuckdbTable: f.source_duckdb_table,
        targetDuckdbSchema: "metrics",
        targetDuckdbTable: f.target_duckdb_table,
        sourcePlugin: this.source,
        description: f.description,
        sql: f.sql,
      },
    });
    if (ok) {
      this._message = { type: "success", text: "Transform created" };
      this._creating = false;
      this._newForm = this._emptyForm();
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: data?.detail || "Create failed" };
    }
  }

  async _preview() {
    const { ok, data } = await gqlFull(this.apiBase, `mutation($id: Int!) { testTransform(transformId: $id, limit: 5) }`, { id: this._editing });
    if (ok) {
      this._previewRows = data?.testTransform;
    } else {
      this._message = {
        type: "error",
        text: data?.detail || "Preview failed",
      };
    }
  }

  render() {
    if (this._loading) return html``;
    return html`
      <div>
      ${renderMessage(this._message)}
      ${this._editing ? this._renderEditor() : ""}
      ${this._creating ? this._renderCreateForm() : ""}
      <shenas-data-list
        ?show-add=${!this._creating && !this._editing}
        @add=${this._startCreate}
        .columns=${[
          { key: "id", label: "ID", class: "muted" },
          { label: "Source", class: "mono", render: (t) => html`${t.sourceDuckdbSchema}.${t.sourceDuckdbTable} <button style=${_inspectBtnStyle} title="Inspect table" @click=${() => this._inspectTable(t.sourceDuckdbSchema, t.sourceDuckdbTable)}>&#9655;</button>` },
          { label: "Target", class: "mono", render: (t) => html`${t.targetDuckdbSchema}.${t.targetDuckdbTable} <button style=${_inspectBtnStyle} title="Inspect table" @click=${() => this._inspectTable(t.targetDuckdbSchema, t.targetDuckdbTable)}>&#9655;</button>` },
          { label: "Description", render: (t) => html`${t.description || ""}${t.isDefault ? html`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>` : ""}` },
          { label: "Status", render: (t) => html`<status-toggle ?enabled=${t.enabled} toggleable @toggle=${() => this._toggle(t)}></status-toggle>` },
        ]}
        .rows=${this._transforms}
        .rowClass=${(t) => t.enabled ? "" : "disabled-row"}
        .actions=${(t) => html`
          ${!t.isDefault
            ? html`<button @click=${() => this._startEdit(t)}>Edit</button>`
            : html`<button @click=${() => this._startEdit(t)}>View</button>`}
          ${!t.isDefault
            ? html`<button class="danger" @click=${() => this._delete(t)}>Delete</button>`
            : ""}
        `}
        empty-text="No transforms"
      ></shenas-data-list>
      </div>
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
    const readonly = t.isDefault;
    return html`
      <div class="edit-panel">
        <h3>
          ${readonly ? "View" : "Edit"}: ${t.sourceDuckdbSchema}.${t.sourceDuckdbTable} ->
          ${t.targetDuckdbSchema}.${t.targetDuckdbTable}
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
