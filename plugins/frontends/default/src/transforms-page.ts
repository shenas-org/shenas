import { LitElement, html, css } from "lit";
import {
  gql,
  gqlFull,
  registerCommands,
  renderMessage,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
} from "shenas-frontends";
import type { MessageBanner } from "shenas-frontends";

const _inspectBtnStyle =
  "background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";

interface Transform {
  id: number;
  transformType: string;
  source: { id: string; schemaName: string; tableName: string; displayName: string };
  target: { id: string; schemaName: string; tableName: string; displayName: string };
  sourcePlugin: string;
  description: string;
  params: string;
  isDefault: boolean;
  enabled: boolean;
}

interface TransformForm {
  transform_type: string;
  source_duckdb_table: string;
  target_duckdb_table: string;
  description: string;
  sql: string;
  params: Record<string, string>;
}

interface ParamField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  description: string;
  default: string | null;
  options: string[] | null;
}

interface TransformTypeInfo {
  name: string;
  displayName: string;
  description: string;
  paramSchema: ParamField[];
}

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
    _transformTypes: { state: true },
    _sourceColumns: { state: true },
    _targetColumns: { state: true },
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

  declare apiBase: string;
  declare source: string;
  declare _transforms: Transform[];
  declare _loading: boolean;
  declare _editing: number | null;
  declare _editSql: string;
  declare _message: MessageBanner | null;
  declare _previewRows: Record<string, unknown>[] | null;
  declare _creating: boolean;
  declare _newForm: TransformForm;
  declare _dbTables: Record<string, string[]>;
  declare _schemaTables: Record<string, string[]>;
  declare _transformTypes: TransformTypeInfo[];
  declare _sourceColumns: string[];
  declare _targetColumns: string[];

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
    this._transformTypes = [];
    this._sourceColumns = [];
    this._targetColumns = [];
  }

  _emptyForm(): TransformForm {
    return {
      transform_type: "sql",
      source_duckdb_table: "",
      target_duckdb_table: "",
      description: "",
      sql: "",
      params: {},
    };
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll(): Promise<void> {
    this._loading = true;
    const data = await gql(
      this.apiBase,
      `query($source: String) { transforms(source: $source) { id transformType source { id schemaName tableName displayName } target { id schemaName tableName displayName } sourcePlugin params description isDefault enabled sql } }`,
      { source: this.source || null },
    );
    this._transforms = (data?.transforms as Transform[]) || [];
    this._loading = false;
    this._registerCommands();
  }

  async _ensureTransformTypes(): Promise<void> {
    if (this._transformTypes.length) return;
    const data = await gql(
      this.apiBase,
      `{ transformTypes { name displayName description paramSchema { name label type required description default options } } }`,
    );
    this._transformTypes = (data?.transformTypes as TransformTypeInfo[]) || [];
  }

  async _fetchColumns(schema: string, table: string): Promise<string[]> {
    if (!schema || !table) return [];
    const data = await gql(this.apiBase, `query($s: String!, $t: String!) { tableColumns(schema: $s, table: $t) }`, {
      s: schema,
      t: table,
    });
    return (data?.tableColumns as string[]) || [];
  }

  async _onSourceTableSelected(table: string): Promise<void> {
    this._updateNewForm("source_duckdb_table", table);
    this._sourceColumns = await this._fetchColumns(this.source, table);
  }

  async _onTargetTableSelected(table: string): Promise<void> {
    this._updateNewForm("target_duckdb_table", table);
    // Target schema is always "metrics" for now
    this._targetColumns = await this._fetchColumns("metrics", table);
  }

  _typeInfoFor(name: string): TransformTypeInfo | undefined {
    return this._transformTypes.find((t) => t.name === name);
  }

  // -- Commands ------------------------------------------------------------

  _registerCommands(): void {
    const commands: Array<{ id: string; category: string; label: string; description?: string; action: () => void }> =
      [];
    for (const t of this._transforms) {
      const desc = t.description || `${t.source.tableName} -> ${t.target.tableName}`;
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

  _inspectTable(schema: string, table: string): void {
    this.dispatchEvent(
      new CustomEvent("inspect-table", {
        bubbles: true,
        composed: true,
        detail: { schema, table },
      }),
    );
  }

  async _toggle(t: Transform): Promise<void> {
    const mutation = t.enabled
      ? `mutation($id: Int!) { disableTransform(transformId: $id) { id enabled } }`
      : `mutation($id: Int!) { enableTransform(transformId: $id) { id enabled } }`;
    await gqlFull(this.apiBase, mutation, { id: t.id });
    await this._fetchAll();
  }

  async _delete(t: Transform): Promise<void> {
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($id: Int!) { deleteTransform(transformId: $id) { ok message } }`,
      { id: t.id },
    );
    if (ok && (data?.deleteTransform as Record<string, unknown>)?.ok) {
      this._message = { type: "success", text: `Deleted transform #${t.id}` };
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Delete failed" };
    }
  }

  _startEdit(t: Transform): void {
    this._editing = t.id;
    this._editSql = t.sql;
    this._previewRows = null;
  }

  _cancelEdit(): void {
    this._editing = null;
    this._editSql = "";
    this._previewRows = null;
  }

  async _saveEdit(): Promise<void> {
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($id: Int!, $sql: String!) { updateTransform(transformId: $id, sql: $sql) { id } }`,
      { id: this._editing, sql: this._editSql },
    );
    if (ok) {
      this._message = { type: "success", text: "Transform updated" };
      this._editing = null;
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Update failed" };
    }
  }

  async _startCreate(): Promise<void> {
    this._creating = true;
    this._newForm = this._emptyForm();
    this._editing = null;
    this._previewRows = null;
    const data = await gql(
      this.apiBase,
      `{ dbTables schemaTables transformTypes { name displayName description paramSchema { name label type required description default options } } }`,
    );
    this._dbTables = (data?.dbTables as Record<string, string[]>) || {};
    this._schemaTables = (data?.schemaTables as Record<string, string[]>) || {};
    this._transformTypes = (data?.transformTypes as TransformTypeInfo[]) || [];
    // Show create form in app-shell's right panel
    this._showCreatePanel();
  }

  _cancelCreate(): void {
    this._creating = false;
    this._newForm = this._emptyForm();
    this._panelEl = null;
    this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
  }

  _updateNewForm(field: keyof TransformForm, value: string): void {
    this._newForm = { ...this._newForm, [field]: value };
    // Re-render the panel if open
    if (this._creating && this._panelEl) this._showCreatePanel();
  }

  private _panelEl: HTMLElement | null = null;

  _showCreatePanel(): void {
    const pipe = this.source;
    const f = this._newForm;
    const sourceTables = this._dbTables[pipe] || [];
    const allSchemaTables = Object.values(this._schemaTables || {}).flat();

    if (!this._panelEl) {
      this._panelEl = document.createElement("div");
      this._panelEl.style.padding = "1rem";
    }
    const panel = this._panelEl;
    const types = this._transformTypes;
    const selectedType = this._typeInfoFor(f.transform_type || "sql");
    const paramFields = selectedType?.paramSchema || [];
    const _lbl = "display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem";
    const _inp = "padding:0.4rem;border:1px solid #ddd;border-radius:4px";

    panel.innerHTML = `
      <h3 style="margin:0 0 1rem;font-size:1rem">New transform</h3>
      <div style="display:flex;flex-direction:column;gap:0.8rem">
        <label style="${_lbl}">
          Transform type
          <select id="xform-type" style="${_inp}">
            ${types.map((t) => `<option value="${t.name}" ${(f.transform_type || "sql") === t.name ? "selected" : ""}>${t.displayName}</option>`).join("")}
          </select>
          ${selectedType?.description ? `<span style="font-size:0.75rem;color:#888">${selectedType.description}</span>` : ""}
        </label>
        <label style="${_lbl}">
          Source table
          <select id="src-table" style="${_inp}">
            <option value="">-- select --</option>
            ${sourceTables.map((t) => `<option value="${t}" ${f.source_duckdb_table === t ? "selected" : ""}>${t}</option>`).join("")}
          </select>
        </label>
        <label style="${_lbl}">
          Target table
          <select id="tgt-table" style="${_inp}">
            <option value="">-- select --</option>
            ${allSchemaTables.map((t) => `<option value="${t}" ${f.target_duckdb_table === t ? "selected" : ""}>${t}</option>`).join("")}
          </select>
        </label>
        <label style="${_lbl}">
          Description
          <input id="desc" value="${f.description}" style="${_inp}" />
        </label>
        ${paramFields
          .map(
            (p) => `
          <label style="${_lbl}">
            ${p.label || _humanize(p.name)}${p.required ? " *" : ""}
            ${
              p.type === "select" && p.options
                ? `<select id="param-${p.name}" style="${_inp}">
                  ${p.options.map((o) => `<option value="${o}" ${(f.params[p.name] || p.default || "") === o ? "selected" : ""}>${o}</option>`).join("")}
                </select>`
                : p.type === "textarea"
                  ? `<textarea id="param-${p.name}" rows="4" style="${_inp};font-family:monospace;font-size:0.85rem">${f.params[p.name] || p.default || ""}</textarea>`
                  : `<input id="param-${p.name}" value="${f.params[p.name] || p.default || ""}" style="${_inp}" ${p.type === "number" ? 'type="number"' : ""} />`
            }
            ${p.description ? `<span style="font-size:0.75rem;color:#888">${p.description}</span>` : ""}
          </label>
        `,
          )
          .join("")}
        <div style="display:flex;gap:0.5rem;justify-content:flex-end;margin-top:0.5rem">
          <button id="create-btn" style="padding:0.4rem 1rem;border:1px solid #ccc;border-radius:4px;cursor:pointer;background:#fff">Create</button>
          <button id="cancel-btn" style="padding:0.4rem 1rem;border:1px solid #ccc;border-radius:4px;cursor:pointer;background:#fff">Cancel</button>
        </div>
      </div>
    `;
    panel.querySelector("#xform-type")?.addEventListener("change", (e) => {
      this._updateNewForm("transform_type", (e.target as HTMLSelectElement).value);
    });
    panel
      .querySelector("#src-table")
      ?.addEventListener("change", (e) =>
        this._updateNewForm("source_duckdb_table", (e.target as HTMLSelectElement).value),
      );
    panel
      .querySelector("#tgt-table")
      ?.addEventListener("change", (e) =>
        this._updateNewForm("target_duckdb_table", (e.target as HTMLSelectElement).value),
      );
    panel
      .querySelector("#desc")
      ?.addEventListener("input", (e) => this._updateNewForm("description", (e.target as HTMLInputElement).value));
    for (const p of paramFields) {
      panel.querySelector(`#param-${p.name}`)?.addEventListener("input", (e) => {
        const val = (e.target as HTMLInputElement).value;
        this._newForm = { ...this._newForm, params: { ...this._newForm.params, [p.name]: val } };
      });
      panel.querySelector(`#param-${p.name}`)?.addEventListener("change", (e) => {
        const val = (e.target as HTMLSelectElement).value;
        this._newForm = { ...this._newForm, params: { ...this._newForm.params, [p.name]: val } };
      });
    }
    panel.querySelector("#create-btn")?.addEventListener("click", () => this._saveCreate());
    panel.querySelector("#cancel-btn")?.addEventListener("click", () => this._cancelCreate());

    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 420 } }),
    );
  }

  async _saveCreate(): Promise<void> {
    const f = this._newForm;
    if (!f.source_duckdb_table || !f.target_duckdb_table) {
      this._message = { type: "error", text: "Source and target tables are required" };
      return;
    }
    // Build params JSON from form fields + sql
    const params: Record<string, string> = { ...f.params };
    if (f.sql) params.sql = f.sql;
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($input: TransformCreateInput!) { createTransform(transformInput: $input) { id } }`,
      {
        input: {
          transformType: f.transform_type || "sql",
          sourceDuckdbSchema: this.source,
          sourceDuckdbTable: f.source_duckdb_table,
          targetDuckdbSchema: "metrics",
          targetDuckdbTable: f.target_duckdb_table,
          sourcePlugin: this.source,
          params: JSON.stringify(params),
          description: f.description,
        },
      },
    );
    if (ok) {
      this._message = { type: "success", text: "Transform created" };
      this._creating = false;
      this._newForm = this._emptyForm();
      this._panelEl = null;
      this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: (data?.detail as string) || "Create failed" };
    }
  }

  async _preview(): Promise<void> {
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($id: Int!) { testTransform(transformId: $id, limit: 5) }`,
      { id: this._editing },
    );
    if (ok) {
      this._previewRows = data?.testTransform as Record<string, unknown>[] | null;
    } else {
      this._message = {
        type: "error",
        text: (data?.detail as string) || "Preview failed",
      };
    }
  }

  render() {
    if (this._loading) return html``;
    return html`
      <div>
        ${renderMessage(this._message)} ${this._editing ? this._renderEditor() : ""}
        <shenas-data-list
          ?show-add=${!this._creating && !this._editing}
          @add=${this._startCreate}
          .columns=${[
            { key: "id", label: "ID", class: "muted" },
            {
              label: "Source",
              class: "mono",
              render: (t: Transform) =>
                html`${t.source.schemaName}.${t.source.tableName}
                  <button
                    style=${_inspectBtnStyle}
                    title="Inspect table"
                    @click=${() => this._inspectTable(t.source.schemaName, t.source.tableName)}
                  >
                    &#9655;
                  </button>`,
            },
            {
              label: "Target",
              class: "mono",
              render: (t: Transform) =>
                html`${t.target.schemaName}.${t.target.tableName}
                  <button
                    style=${_inspectBtnStyle}
                    title="Inspect table"
                    @click=${() => this._inspectTable(t.target.schemaName, t.target.tableName)}
                  >
                    &#9655;
                  </button>`,
            },
            {
              label: "Description",
              render: (t: Transform) =>
                html`${t.description || ""}${t.isDefault
                  ? html`<span
                      style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px"
                      >default</span
                    >`
                  : ""}`,
            },
            {
              label: "Status",
              render: (t: Transform) =>
                html`<status-toggle ?enabled=${t.enabled} toggleable @toggle=${() => this._toggle(t)}></status-toggle>`,
            },
          ]}
          .rows=${this._transforms}
          .rowClass=${(t: Transform) => (t.enabled ? "" : "disabled-row")}
          .actions=${(t: Transform) => html`
            ${!t.isDefault
              ? html`<button @click=${() => this._startEdit(t)}>Edit</button>`
              : html`<button @click=${() => this._startEdit(t)}>View</button>`}
            ${!t.isDefault ? html`<button class="danger" @click=${() => this._delete(t)}>Delete</button>` : ""}
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
              @change=${(e: Event) => this._updateNewForm("source_duckdb_table", (e.target as HTMLSelectElement).value)}
            >
              <option value="">-- select --</option>
              ${sourceTables.map(
                (t) => html`<option value=${t} ?selected=${f.source_duckdb_table === t}>${t}</option>`,
              )}
            </select>
          </label>
          <label>
            Schema table
            <select
              .value=${f.target_duckdb_table}
              @change=${(e: Event) => this._updateNewForm("target_duckdb_table", (e.target as HTMLSelectElement).value)}
            >
              <option value="">-- select --</option>
              ${allSchemaTables.map(
                (t) => html`<option value=${t} ?selected=${f.target_duckdb_table === t}>${t}</option>`,
              )}
            </select>
          </label>
          <label class="form-full">
            Description
            <input
              .value=${f.description}
              @input=${(e: InputEvent) => this._updateNewForm("description", (e.target as HTMLInputElement).value)}
            />
          </label>
        </div>
        <textarea
          .value=${f.sql}
          @input=${(e: InputEvent) => this._updateNewForm("sql", (e.target as HTMLTextAreaElement).value)}
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
          ${readonly ? "View" : "Edit"}: ${t.source.schemaName}.${t.source.tableName} ->
          ${t.target.schemaName}.${t.target.tableName}
        </h3>
        <textarea
          .value=${this._editSql}
          @input=${(e: InputEvent) => (this._editSql = (e.target as HTMLTextAreaElement).value)}
          ?readonly=${readonly}
          class="${readonly ? "readonly" : ""}"
        ></textarea>
        <div class="edit-actions">
          ${!readonly ? html`<button @click=${this._saveEdit}>Save</button>` : ""}
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
