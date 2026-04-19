import { LitElement, html, css } from "lit";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  registerCommands,
  renderMessage,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
} from "shenas-frontends";
import type { MessageBanner } from "shenas-frontends";
import { GET_TRANSFORMS, GET_TABLE_COLUMNS, GET_CATEGORY_SETS } from "./graphql/queries.ts";
import {
  CREATE_TRANSFORM,
  UPDATE_TRANSFORM,
  DELETE_TRANSFORM,
  ENABLE_TRANSFORM,
  DISABLE_TRANSFORM,
  TEST_TRANSFORM,
} from "./graphql/mutations.ts";

interface Transform {
  id: number;
  transformType: string;
  source: { id: string; schemaName: string; tableName: string; displayName: string };
  target: { id: string; schemaName: string; tableName: string; displayName: string };
  sourcePlugin: string;
  description: string;
  params: string;
  sql: string;
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
  visible_when?: Record<string, string> | null;
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
    sourceTables: { type: Array },
    targetTables: { type: Array },
    showSuggest: { type: Boolean, attribute: "show-suggest" },
    suggesting: { type: Boolean },
    _transforms: { state: true },
    _loading: { state: true },
    _editing: { state: true },
    _editSql: { state: true },
    _message: { state: true },
    _previewRows: { state: true },
    _creating: { state: true },
    _newForm: { state: true },
    _transformTypes: { state: true },
    _sourceColumns: { state: true },
    _targetColumns: { state: true },
    _categorySets: { state: true },
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
  declare sourceTables: { table: string; display_name: string }[];
  declare targetTables: string[];
  declare showSuggest: boolean;
  declare suggesting: boolean;
  declare _transforms: Transform[];
  declare _loading: boolean;
  declare _editing: number | null;
  declare _editSql: string;
  declare _message: MessageBanner | null;
  declare _previewRows: Record<string, unknown>[] | null;
  declare _creating: boolean;
  declare _newForm: TransformForm;
  declare _transformTypes: TransformTypeInfo[];
  declare _sourceColumns: string[];
  declare _targetColumns: string[];
  declare _categorySets: Array<{ displayName: string; values: Array<{ value: string }> }>;

  private _client = getClient();

  private _transformsQuery = new ApolloQueryController(this, GET_TRANSFORMS, {
    client: this._client,
    noAutoSubscribe: true,
  });

  private _enableTransform = new ApolloMutationController(this, ENABLE_TRANSFORM, { client: this._client });
  private _disableTransform = new ApolloMutationController(this, DISABLE_TRANSFORM, { client: this._client });
  private _deleteTransform = new ApolloMutationController(this, DELETE_TRANSFORM, { client: this._client });
  private _updateTransform = new ApolloMutationController(this, UPDATE_TRANSFORM, { client: this._client });
  private _createTransform = new ApolloMutationController(this, CREATE_TRANSFORM, { client: this._client });
  private _testTransform = new ApolloMutationController(this, TEST_TRANSFORM, { client: this._client });

  constructor() {
    super();
    this.apiBase = "/api";
    this.source = "";
    this.showSuggest = false;
    this.suggesting = false;
    this._transforms = [];
    this._loading = true;
    this._editing = null;
    this._editSql = "";
    this._message = null;
    this._previewRows = null;
    this._creating = false;
    this._newForm = this._emptyForm();
    this._transformTypes = [];
    this._sourceColumns = [];
    this._targetColumns = [];
    this._categorySets = [];
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
    const { data } = await this._client.query({
      query: GET_TRANSFORMS,
      variables: { source: this.source || null },
      fetchPolicy: "network-only",
    });
    this._transforms = (data?.transforms as Transform[]) || [];
    this._transformTypes = (data?.transformTypes as TransformTypeInfo[]) || [];
    this._loading = false;
    this._registerCommands();
  }

  async _ensureCategorySets(): Promise<void> {
    if (this._categorySets.length) return;
    const { data } = await this._client.query({ query: GET_CATEGORY_SETS });
    this._categorySets = (data?.categorySets as Array<{ displayName: string; values: Array<{ value: string }> }>) || [];
  }

  async _fetchColumns(schema: string, table: string): Promise<string[]> {
    if (!schema || !table) return [];
    const { data } = await this._client.query({
      query: GET_TABLE_COLUMNS,
      variables: { s: schema, t: table },
      fetchPolicy: "network-only",
    });
    return (data?.tableColumns as string[]) || [];
  }

  async _onSourceTableSelected(table: string): Promise<void> {
    this._updateNewForm("source_duckdb_table", table);
    this._sourceColumns = await this._fetchColumns(this.source, table);
  }

  async _onTargetTableSelected(table: string): Promise<void> {
    this._updateNewForm("target_duckdb_table", table);
    // Target schema is always "datasets" for now
    this._targetColumns = await this._fetchColumns("datasets", table);
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
    const controller = t.enabled ? this._disableTransform : this._enableTransform;
    await controller.mutate({ variables: { id: t.id } });
    await this._fetchAll();
  }

  async _delete(t: Transform): Promise<void> {
    try {
      const { data } = await this._deleteTransform.mutate({ variables: { id: t.id } });
      if ((data?.deleteTransform as Record<string, unknown>)?.ok) {
        this._message = { type: "success", text: `Deleted transform #${t.id}` };
        await this._fetchAll();
      } else {
        this._message = { type: "error", text: "Delete failed" };
      }
    } catch {
      this._message = { type: "error", text: "Delete failed" };
    }
  }

  _startEdit(t: Transform): void {
    this._editing = t.id;
    this._editSql = t.sql;
    this._previewRows = null;
  }

  _openViewPanel(t: Transform): void {
    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    const _lbl = "display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem;margin-bottom:0.6rem";
    const _val = "padding:0.4rem;border:1px solid #eee;border-radius:4px;background:#f9f9f9;font-size:0.85rem";
    const params = typeof t.params === "string" ? JSON.parse(t.params || "{}") : t.params || {};
    const paramEntries = Object.entries(params).filter(([k]) => k !== "sql");
    panel.innerHTML = `
      <h3 style="margin:0 0 1rem;font-size:1rem">
        View: ${t.source.displayName || t.source.tableName} -> ${t.target.displayName || t.target.tableName}
      </h3>
      <div style="display:flex;flex-direction:column;gap:0.4rem">
        <div style="${_lbl}">
          <span style="font-weight:600">Type</span>
          <span style="${_val}">${t.transformType}</span>
        </div>
        <div style="${_lbl}">
          <span style="font-weight:600">Source</span>
          <span style="${_val}">${t.source.schemaName}.${t.source.tableName}</span>
        </div>
        <div style="${_lbl}">
          <span style="font-weight:600">Target</span>
          <span style="${_val}">${t.target.schemaName}.${t.target.tableName}</span>
        </div>
        ${t.description ? `<div style="${_lbl}"><span style="font-weight:600">Description</span><span style="${_val}">${t.description}</span></div>` : ""}
        ${paramEntries.map(([k, v]) => `<div style="${_lbl}"><span style="font-weight:600">${k}</span><span style="${_val};white-space:pre-wrap">${v}</span></div>`).join("")}
        ${t.sql ? `<div style="${_lbl}"><span style="font-weight:600">SQL</span><textarea readonly style="${_val};font-family:monospace;resize:vertical;min-height:6rem;white-space:pre;overflow:auto">${t.sql}</textarea></div>` : ""}
        <div style="display:flex;gap:0.5rem;justify-content:flex-end;margin-top:0.5rem">
          <button id="close-btn" style="padding:0.4rem 1rem;border:1px solid #ccc;border-radius:4px;cursor:pointer;background:#fff">Close</button>
        </div>
      </div>
    `;
    panel.querySelector("#close-btn")?.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
    });
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 480 } }),
    );
  }

  _cancelEdit(): void {
    this._editing = null;
    this._editSql = "";
    this._previewRows = null;
  }

  async _saveEdit(): Promise<void> {
    try {
      await this._updateTransform.mutate({ variables: { id: this._editing, sql: this._editSql } });
      this._message = { type: "success", text: "Transform updated" };
      this._editing = null;
      await this._fetchAll();
    } catch {
      this._message = { type: "error", text: "Update failed" };
    }
  }

  _onSuggest(): void {
    this.dispatchEvent(new CustomEvent("suggest", { bubbles: true, composed: true }));
  }

  async _startCreate(): Promise<void> {
    this._creating = true;
    this._newForm = this._emptyForm();
    this._editing = null;
    this._previewRows = null;
    await this._ensureCategorySets();
    this._showCreatePanel();
  }

  _cancelCreate(): void {
    this._creating = false;
    this._newForm = this._emptyForm();
    this._panelEl = null;
    this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
  }

  async _updateNewForm(field: keyof TransformForm, value: string): Promise<void> {
    this._newForm = { ...this._newForm, [field]: value };
    // Auto-generate SQL when source table changes
    if (field === "source_duckdb_table" && value && this._newForm.transform_type === "sql") {
      const cols = await this._fetchColumns(this.source, value);
      if (cols.length > 0) {
        const colList = cols.filter((c) => !c.startsWith("_dlt_")).join(",\n       ");
        const target = this._newForm.target_duckdb_table;
        const deleteClause = target ? `DELETE FROM metrics.${target} WHERE source = '${this.source}';\n` : "";
        const insertInto = target ? `INSERT INTO metrics.${target}\n` : "";
        this._newForm = {
          ...this._newForm,
          sql: `${deleteClause}${insertInto}SELECT ${colList}\nFROM ${this.source}.${value}`,
        };
      }
    }
    // Re-render the panel if open
    if (this._creating && this._panelEl) this._showCreatePanel();
  }

  private _panelEl: HTMLElement | null = null;

  _showCreatePanel(): void {
    const f = this._newForm;
    const sourceTableNames = (this.sourceTables || []).map((entry) => entry.table);
    const targetTableNames = this.targetTables || [];

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

    const renderParam = (p: ParamField): string => {
      if (p.visible_when) {
        const hidden = Object.entries(p.visible_when).some(([k, v]) => (f.params[k] || "") !== v);
        if (hidden) return "";
      }
      const val = f.params[p.name] || p.default || "";
      let control: string;
      if (p.type === "source_column") {
        const cols = this._sourceColumns.filter((c: string) => !c.startsWith("_dlt_"));
        control = `<select id="param-${p.name}" style="${_inp}">
          <option value="">-- select --</option>
          ${cols.map((c: string) => `<option value="${c}" ${val === c ? "selected" : ""}>${c}</option>`).join("")}
        </select>`;
      } else if (p.type === "target_column") {
        const cols = this._targetColumns.filter((c: string) => !c.startsWith("_dlt_"));
        control = `<select id="param-${p.name}" style="${_inp}">
          <option value="">-- select --</option>
          ${cols.map((c: string) => `<option value="${c}" ${val === c ? "selected" : ""}>${c}</option>`).join("")}
        </select>`;
      } else if (p.type === "category_set") {
        const sets = this._categorySets || [];
        control = `<select id="param-${p.name}" style="${_inp}">
          <option value="">-- select --</option>
          ${sets.map((s: { displayName: string; values: Array<{ value: string }> }) => `<option value="${s.values.map((v: { value: string }) => v.value).join(",")}" ${val === s.values.map((v: { value: string }) => v.value).join(",") ? "selected" : ""}>${s.displayName}</option>`).join("")}
        </select>`;
      } else if (p.type === "select" && p.options) {
        control = `<select id="param-${p.name}" style="${_inp}">
          ${p.options.map((o: string) => `<option value="${o}" ${val === o ? "selected" : ""}>${o}</option>`).join("")}
        </select>`;
      } else if (p.type === "textarea") {
        control = `<textarea id="param-${p.name}" rows="4" style="${_inp};font-family:monospace;font-size:0.85rem">${val}</textarea>`;
      } else {
        control = `<input id="param-${p.name}" value="${val}" style="${_inp}" ${p.type === "number" ? 'type="number"' : ""} />`;
      }
      return `
        <label style="${_lbl}">
          ${p.label}${p.required ? " *" : ""}
          ${control}
          ${p.description ? `<span style="font-size:0.75rem;color:#888">${p.description}</span>` : ""}
        </label>`;
    };
    const sourceParams = paramFields.filter((p) => p.type === "source_column");
    const targetParams = paramFields.filter((p) => p.type === "target_column");
    const otherParams = paramFields.filter((p) => p.type !== "source_column" && p.type !== "target_column");

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
            ${sourceTableNames.map((name) => `<option value="${name}" ${f.source_duckdb_table === name ? "selected" : ""}>${name}</option>`).join("")}
          </select>
        </label>
        ${sourceParams.map(renderParam).join("")}
        <label style="${_lbl}">
          Target table
          <select id="tgt-table" style="${_inp}">
            <option value="">-- select --</option>
            ${targetTableNames.map((name) => `<option value="${name}" ${f.target_duckdb_table === name ? "selected" : ""}>${name}</option>`).join("")}
          </select>
        </label>
        ${targetParams.map(renderParam).join("")}
        ${otherParams.map(renderParam).join("")}
        <label style="${_lbl}">
          Description
          <textarea id="desc" rows="2" style="${_inp}">${f.description}</textarea>
        </label>
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
      ?.addEventListener("change", (e) => this._onSourceTableSelected((e.target as HTMLSelectElement).value));
    panel
      .querySelector("#tgt-table")
      ?.addEventListener("change", (e) => this._onTargetTableSelected((e.target as HTMLSelectElement).value));
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
        // Re-render when a select changes so visible_when conditions update
        if (p.type === "select") this._showCreatePanel();
      });
    }
    panel.querySelector("#create-btn")?.addEventListener("click", () => this._saveCreate());
    panel.querySelector("#cancel-btn")?.addEventListener("click", () => this._cancelCreate());

    // Fetch columns for pre-selected tables so the dropdowns are populated
    // on first render (change events only fire on user interaction).
    if (f.source_duckdb_table && this._sourceColumns.length === 0) {
      this._fetchColumns(this.source, f.source_duckdb_table).then((cols) => {
        this._sourceColumns = cols;
        this._showCreatePanel();
      });
    }
    if (f.target_duckdb_table && this._targetColumns.length === 0) {
      this._fetchColumns("datasets", f.target_duckdb_table).then((cols) => {
        this._targetColumns = cols;
        this._showCreatePanel();
      });
    }

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
    try {
      await this._createTransform.mutate({
        variables: {
          input: {
            transformType: f.transform_type || "sql",
            sourceDuckdbSchema: this.source,
            sourceDuckdbTable: f.source_duckdb_table,
            targetDuckdbSchema: "datasets",
            targetDuckdbTable: f.target_duckdb_table,
            sourcePlugin: this.source,
            params: JSON.stringify(params),
            description: f.description,
          },
        },
      });
      this._message = { type: "success", text: "Transform created" };
      this._creating = false;
      this._newForm = this._emptyForm();
      this._panelEl = null;
      this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
      await this._fetchAll();
    } catch {
      this._message = { type: "error", text: "Create failed" };
    }
  }

  async _preview(): Promise<void> {
    try {
      const { data } = await this._testTransform.mutate({ variables: { id: this._editing } });
      this._previewRows = data?.testTransform as Record<string, unknown>[] | null;
    } catch {
      this._message = { type: "error", text: "Preview failed" };
    }
  }

  render() {
    if (this._loading) return html``;
    return html`
      <div>
        ${renderMessage(this._message)} ${this._editing ? this._renderEditor() : ""}
        ${this.showSuggest || !this._creating
          ? html`<div style="display:flex;justify-content:flex-end;gap:0.5rem;margin-bottom:0.5rem">
              ${this.showSuggest
                ? html`<button @click=${this._onSuggest} ?disabled=${this.suggesting}>
                    ${this.suggesting ? "Generating..." : "Suggest Metrics"}
                  </button>`
                : ""}
              ${!this._creating && !this._editing ? html`<button @click=${this._startCreate}>Add</button>` : ""}
            </div>`
          : ""}
        <shenas-data-list
          .showAdd=${false}
          @add=${this._startCreate}
          .columns=${[
            { key: "id", label: "ID", class: "muted" },
            {
              label: "Source",
              render: (t: Transform) =>
                html`<span
                  style="cursor:pointer;color:var(--shenas-text,#333);text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                  title="${t.source.schemaName}.${t.source.tableName}"
                  @click=${() => this._inspectTable(t.source.schemaName, t.source.tableName)}
                  >${t.source.displayName || t.source.tableName}</span
                >`,
            },
            {
              label: "Target",
              render: (t: Transform) =>
                html`<span
                  style="cursor:pointer;color:var(--shenas-text,#333);text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                  title="${t.target.schemaName}.${t.target.tableName}"
                  @click=${() => this._inspectTable(t.target.schemaName, t.target.tableName)}
                  >${t.target.displayName || t.target.tableName}</span
                >`,
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
              : html`<button @click=${() => this._openViewPanel(t)}>View</button>`}
            ${!t.isDefault ? html`<button class="danger" @click=${() => this._delete(t)}>Delete</button>` : ""}
          `}
          empty-text="No transforms"
        ></shenas-data-list>
      </div>
    `;
  }

  _renderCreateForm() {
    const f = this._newForm;
    const sourceTableNames = (this.sourceTables || []).map((entry) => entry.table);
    const targetTableNames = this.targetTables || [];
    return html`
      <shenas-form-panel
        title="New transform"
        submit-label="Create"
        @submit=${this._saveCreate}
        @cancel=${this._cancelCreate}
      >
        <div class="form-grid">
          <label>
            Source table
            <select
              .value=${f.source_duckdb_table}
              @change=${(e: Event) => this._updateNewForm("source_duckdb_table", (e.target as HTMLSelectElement).value)}
            >
              <option value="">-- select --</option>
              ${sourceTableNames.map(
                (name) => html`<option value=${name} ?selected=${f.source_duckdb_table === name}>${name}</option>`,
              )}
            </select>
          </label>
          <label>
            Target table
            <select
              .value=${f.target_duckdb_table}
              @change=${(e: Event) => this._updateNewForm("target_duckdb_table", (e.target as HTMLSelectElement).value)}
            >
              <option value="">-- select --</option>
              ${targetTableNames.map(
                (name) => html`<option value=${name} ?selected=${f.target_duckdb_table === name}>${name}</option>`,
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
          placeholder="SELECT ... FROM sources.${f.source_duckdb_table || "table_name"}"
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
          ${readonly ? "View" : "Edit"}: ${t.source.displayName || t.source.tableName} ->
          ${t.target.displayName || t.target.tableName}
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
