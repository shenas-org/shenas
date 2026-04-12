import { LitElement, html, css, nothing } from "lit";
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

const _inspectBtnStyle =
  "background:none;border:none;cursor:pointer;color:var(--shenas-text-faint, #aaa);font-size:0.7rem;padding:0 2px";

/** Convert snake_case to Title Case (e.g. "latitude_column" -> "Latitude column"). */
function _humanize(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/^./, (c) => c.toUpperCase());
}

interface Transform {
  id: number;
  transformType: string;
  sourceDuckdbSchema: string;
  sourceDuckdbTable: string;
  targetDuckdbSchema: string;
  targetDuckdbTable: string;
  sourcePlugin: string;
  description: string;
  params: string;
  isDefault: boolean;
  enabled: boolean;
}

interface ParamField {
  name: string;
  label?: string;
  type: string;
  required: boolean;
  description: string;
  default?: string | number;
  options?: string[];
}

interface TransformTypeInfo {
  name: string;
  displayName: string;
  description: string;
  paramSchema: ParamField[];
}

interface TransformForm {
  transform_type: string;
  source_duckdb_table: string;
  target_duckdb_table: string;
  description: string;
  params: Record<string, string>;
}

interface Message {
  type: string;
  text: string;
}

class TransformsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    source: { type: String },
    _transforms: { state: true },
    _loading: { state: true },
    _editing: { state: true },
    _editParams: { state: true },
    _message: { state: true },
    _previewRows: { state: true },
    _creating: { state: true },
    _newForm: { state: true },
    _dbTables: { state: true },
    _schemaTables: { state: true },
    _transformTypes: { state: true },
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
      .param-hint {
        font-size: 0.75rem;
        color: var(--shenas-text-muted, #888);
      }
      .type-desc {
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
        margin: 0.2rem 0 0.6rem;
      }
    `,
  ];

  declare apiBase: string;
  declare source: string;
  declare _transforms: Transform[];
  declare _loading: boolean;
  declare _editing: number | null;
  declare _editParams: Record<string, string>;
  declare _message: Message | null;
  declare _previewRows: Record<string, unknown>[] | null;
  declare _creating: boolean;
  declare _newForm: TransformForm;
  declare _dbTables: Record<string, string[]>;
  declare _schemaTables: Record<string, string[]>;
  declare _transformTypes: TransformTypeInfo[];

  constructor() {
    super();
    this.apiBase = "/api";
    this.source = "";
    this._transforms = [];
    this._loading = true;
    this._editing = null;
    this._editParams = {};
    this._message = null;
    this._previewRows = null;
    this._creating = false;
    this._newForm = this._emptyForm();
    this._dbTables = {};
    this._schemaTables = {};
    this._transformTypes = [];
  }

  _emptyForm(): TransformForm {
    return {
      transform_type: "",
      source_duckdb_table: "",
      target_duckdb_table: "",
      description: "",
      params: {},
    };
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
  }

  // -- Data fetching -------------------------------------------------------

  async _fetchAll(): Promise<void> {
    this._loading = true;
    const data = await gql(
      this.apiBase,
      `query($source: String) {
        transforms(source: $source) {
          id transformType sourceDuckdbSchema sourceDuckdbTable
          targetDuckdbSchema targetDuckdbTable sourcePlugin
          params description isDefault enabled
        }
      }`,
      { source: this.source || null },
    );
    this._transforms = (data?.transforms as Transform[]) || [];
    this._loading = false;
    this._registerCommands();
  }

  async _ensureTransformTypes(): Promise<void> {
    if (this._transformTypes.length) return;
    const data = await gql(this.apiBase, `{ transformTypes }`);
    this._transformTypes =
      (data?.transformTypes as TransformTypeInfo[]) || [];
  }

  _typeInfoFor(name: string): TransformTypeInfo | undefined {
    return this._transformTypes.find((t) => t.name === name);
  }

  // -- Commands ------------------------------------------------------------

  _registerCommands(): void {
    const commands: Array<{
      id: string;
      category: string;
      label: string;
      description?: string;
      action: () => void;
    }> = [];
    for (const t of this._transforms) {
      const desc =
        t.description ||
        `${t.sourceDuckdbTable} -> ${t.targetDuckdbTable}`;
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

  // -- Actions -------------------------------------------------------------

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

  async _preview(): Promise<void> {
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($id: Int!) { testTransform(transformId: $id, limit: 5) }`,
      { id: this._editing },
    );
    if (ok) {
      this._previewRows = data?.testTransform as Record<string, unknown>[] | null;
    } else {
      this._message = { type: "error", text: (data?.detail as string) || "Preview failed" };
    }
  }

  // -- Create --------------------------------------------------------------

  async _startCreate(): Promise<void> {
    this._creating = true;
    this._newForm = this._emptyForm();
    this._editing = null;
    this._previewRows = null;
    const data = await gql(this.apiBase, `{ dbTables schemaTables transformTypes }`);
    this._dbTables = (data?.dbTables as Record<string, string[]>) || {};
    this._schemaTables = (data?.schemaTables as Record<string, string[]>) || {};
    this._transformTypes = (data?.transformTypes as TransformTypeInfo[]) || [];
  }

  _cancelCreate(): void {
    this._creating = false;
    this._newForm = this._emptyForm();
  }

  _updateNewForm(field: keyof TransformForm, value: unknown): void {
    this._newForm = { ...this._newForm, [field]: value };
  }

  _updateNewParam(name: string, value: string): void {
    this._updateNewForm("params", { ...this._newForm.params, [name]: value });
  }

  async _saveCreate(): Promise<void> {
    const f = this._newForm;
    if (!f.transform_type || !f.source_duckdb_table || !f.target_duckdb_table) {
      this._message = { type: "error", text: "Select a transform type, source table, and target table" };
      return;
    }
    const { ok, data } = await gqlFull(
      this.apiBase,
      `mutation($input: TransformCreateInput!) { createTransform(transformInput: $input) { id } }`,
      {
        input: {
          transformType: f.transform_type,
          sourceDuckdbSchema: this.source,
          sourceDuckdbTable: f.source_duckdb_table,
          targetDuckdbSchema: "metrics",
          targetDuckdbTable: f.target_duckdb_table,
          sourcePlugin: this.source,
          description: f.description,
          params: JSON.stringify(f.params),
        },
      },
    );
    if (ok) {
      this._message = { type: "success", text: "Transform created" };
      this._creating = false;
      this._newForm = this._emptyForm();
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: (data?.detail as string) || "Create failed" };
    }
  }

  // -- Edit ----------------------------------------------------------------

  async _startEdit(t: Transform): Promise<void> {
    this._editing = t.id;
    try {
      this._editParams = JSON.parse(t.params || "{}");
    } catch {
      this._editParams = {};
    }
    this._previewRows = null;
    await this._ensureTransformTypes();
  }

  _cancelEdit(): void {
    this._editing = null;
    this._editParams = {};
    this._previewRows = null;
  }

  _updateEditParam(name: string, value: string): void {
    this._editParams = { ...this._editParams, [name]: value };
  }

  async _saveEdit(): Promise<void> {
    const { ok } = await gqlFull(
      this.apiBase,
      `mutation($id: Int!, $params: String!) { updateTransform(transformId: $id, params: $params) { id } }`,
      { id: this._editing, params: JSON.stringify(this._editParams) },
    );
    if (ok) {
      this._message = { type: "success", text: "Transform updated" };
      this._editing = null;
      await this._fetchAll();
    } else {
      this._message = { type: "error", text: "Update failed" };
    }
  }

  // -- Render: main --------------------------------------------------------

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
            {
              label: "Type",
              class: "mono",
              render: (t: Transform) => html`${t.transformType}`,
            },
            {
              label: "Source",
              class: "mono",
              render: (t: Transform) =>
                html`${t.sourceDuckdbSchema}.${t.sourceDuckdbTable}
                  <button style=${_inspectBtnStyle} title="Inspect table"
                    @click=${() => this._inspectTable(t.sourceDuckdbSchema, t.sourceDuckdbTable)}>&#9655;</button>`,
            },
            {
              label: "Target",
              class: "mono",
              render: (t: Transform) =>
                html`${t.targetDuckdbSchema}.${t.targetDuckdbTable}
                  <button style=${_inspectBtnStyle} title="Inspect table"
                    @click=${() => this._inspectTable(t.targetDuckdbSchema, t.targetDuckdbTable)}>&#9655;</button>`,
            },
            {
              label: "Description",
              render: (t: Transform) =>
                html`${t.description || ""}${t.isDefault
                  ? html`<span style="font-size:0.75rem;color:var(--shenas-text-muted, #888);background:var(--shenas-border-light, #f0f0f0);padding:1px 5px;border-radius:3px;margin-left:4px">default</span>`
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
            <button @click=${() => this._startEdit(t)}>${t.isDefault ? "View" : "Edit"}</button>
            ${!t.isDefault ? html`<button class="danger" @click=${() => this._delete(t)}>Delete</button>` : ""}
          `}
          empty-text="No transforms"
        ></shenas-data-list>
      </div>
    `;
  }

  // -- Render: create form -------------------------------------------------

  _renderCreateForm() {
    const f = this._newForm;
    const sourceTables = this._dbTables[this.source] || [];
    const allSchemaTables = Object.values(this._schemaTables || {}).flat();
    const selectedType = this._typeInfoFor(f.transform_type);
    return html`
      <shenas-form-panel title="New transform" submit-label="Create"
        @submit=${this._saveCreate} @cancel=${this._cancelCreate}>
        <div class="form-grid">
          <label class="form-full">
            Transform type
            <select .value=${f.transform_type}
              @change=${(e: Event) => this._updateNewForm("transform_type", (e.target as HTMLSelectElement).value)}>
              <option value="">-- select --</option>
              ${this._transformTypes.map(
                (t) => html`<option value=${t.name} ?selected=${f.transform_type === t.name}>${t.displayName}</option>`,
              )}
            </select>
          </label>
          ${selectedType?.description ? html`<p class="type-desc form-full">${selectedType.description}</p>` : nothing}
          <label>
            Source table
            <select .value=${f.source_duckdb_table}
              @change=${(e: Event) => this._updateNewForm("source_duckdb_table", (e.target as HTMLSelectElement).value)}>
              <option value="">-- select --</option>
              ${sourceTables.map(
                (t) => html`<option value=${t} ?selected=${f.source_duckdb_table === t}>${t}</option>`,
              )}
            </select>
          </label>
          <label>
            Target table
            <select .value=${f.target_duckdb_table}
              @change=${(e: Event) => this._updateNewForm("target_duckdb_table", (e.target as HTMLSelectElement).value)}>
              <option value="">-- select --</option>
              ${allSchemaTables.map(
                (t) => html`<option value=${t} ?selected=${f.target_duckdb_table === t}>${t}</option>`,
              )}
            </select>
          </label>
          <label class="form-full">
            Description
            <input .value=${f.description}
              @input=${(e: InputEvent) => this._updateNewForm("description", (e.target as HTMLInputElement).value)} />
          </label>
        </div>
        ${selectedType ? this._renderParamFields(selectedType.paramSchema, f.params, false, (n, v) => this._updateNewParam(n, v)) : nothing}
      </shenas-form-panel>
    `;
  }

  // -- Render: edit/view panel ---------------------------------------------

  _renderEditor() {
    const t = this._transforms.find((x) => x.id === this._editing);
    if (!t) return "";
    const readonly = t.isDefault;
    const typeInfo = this._typeInfoFor(t.transformType);
    const schema = typeInfo?.paramSchema || [];
    return html`
      <div class="edit-panel">
        <h3>
          ${readonly ? "View" : "Edit"}:
          ${t.sourceDuckdbSchema}.${t.sourceDuckdbTable} ->
          ${t.targetDuckdbSchema}.${t.targetDuckdbTable}
          <span class="param-hint">(${t.transformType})</span>
        </h3>
        ${schema.length
          ? this._renderParamFields(schema, this._editParams, readonly, (n, v) => this._updateEditParam(n, v))
          : html`<textarea
              .value=${JSON.stringify(this._editParams, null, 2)}
              @input=${(e: InputEvent) => {
                try { this._editParams = JSON.parse((e.target as HTMLTextAreaElement).value); } catch { /* typing */ }
              }}
              ?readonly=${readonly} class="${readonly ? "readonly" : ""}"></textarea>`}
        <div class="edit-actions">
          ${!readonly ? html`<button @click=${this._saveEdit}>Save</button>` : ""}
          <button @click=${this._preview}>Preview</button>
          <button @click=${this._cancelEdit}>${readonly ? "Close" : "Cancel"}</button>
        </div>
        ${this._previewRows ? this._renderPreview() : ""}
      </div>
    `;
  }

  // -- Render: shared param fields -----------------------------------------

  _renderParamFields(
    schema: ParamField[],
    values: Record<string, string>,
    readonly: boolean,
    onChange: (name: string, value: string) => void,
  ) {
    if (!schema.length) return nothing;
    return html`
      <div class="form-grid">
        ${schema.map((p) => {
          const val = values[p.name] ?? p.default ?? "";
          const lbl = p.label || _humanize(p.name);
          const req = p.required ? " *" : "";

          if (p.type === "textarea") {
            return html`
              <label class="form-full">
                ${lbl}${req}
                <textarea .value=${String(val)} ?readonly=${readonly} class="${readonly ? "readonly" : ""}"
                  placeholder=${p.description}
                  @input=${(e: InputEvent) => onChange(p.name, (e.target as HTMLTextAreaElement).value)}></textarea>
                ${p.description ? html`<span class="param-hint">${p.description}</span>` : nothing}
              </label>`;
          }
          if (p.type === "select" && p.options) {
            return html`
              <label>
                ${lbl}${req}
                <select .value=${String(val)} ?disabled=${readonly}
                  @change=${(e: Event) => onChange(p.name, (e.target as HTMLSelectElement).value)}>
                  ${p.options.map((o) => html`<option value=${o} ?selected=${String(val) === o}>${o}</option>`)}
                </select>
                ${p.description ? html`<span class="param-hint">${p.description}</span>` : nothing}
              </label>`;
          }
          return html`
            <label>
              ${lbl}${req}
              <input type=${p.type === "number" ? "number" : "text"} .value=${String(val)} ?readonly=${readonly}
                placeholder=${p.description}
                @input=${(e: InputEvent) => onChange(p.name, (e.target as HTMLInputElement).value)} />
              ${p.description ? html`<span class="param-hint">${p.description}</span>` : nothing}
            </label>`;
        })}
      </div>
    `;
  }

  // -- Render: preview table -----------------------------------------------

  _renderPreview() {
    if (!this._previewRows || this._previewRows.length === 0) {
      return html`<p class="loading">No preview rows</p>`;
    }
    const cols = Object.keys(this._previewRows[0]);
    return html`
      <div class="preview-table">
        <table>
          <thead><tr>${cols.map((c) => html`<th>${c}</th>`)}</tr></thead>
          <tbody>
            ${this._previewRows.map((row) => html`<tr>${cols.map((c) => html`<td>${row[c]}</td>`)}</tr>`)}
          </tbody>
        </table>
      </div>
    `;
  }
}

customElements.define("shenas-transforms", TransformsPage);
