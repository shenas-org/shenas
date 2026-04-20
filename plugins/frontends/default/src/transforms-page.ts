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
import {
  GET_TRANSFORMS,
  GET_TABLE_COLUMNS,
  GET_TABLE_METADATA,
  GET_CATEGORY_SETS,
  GET_DATA_RESOURCES,
} from "./graphql/queries.ts";
import "./sql-builder.ts";
import {
  CREATE_TRANSFORM,
  UPDATE_TRANSFORM,
  UPDATE_TRANSFORM_STEPS,
  DELETE_TRANSFORM,
  ENABLE_TRANSFORM,
  DISABLE_TRANSFORM,
  TEST_TRANSFORM,
} from "./graphql/mutations.ts";

interface ParamField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  description: string;
  default: string | null;
  options: string[] | null;
  visible_when?: Record<string, string> | null;
  role?: string | null;
}

interface TransformTypeInfo {
  name: string;
  displayName: string;
  description: string;
  paramSchema: ParamField[];
}

interface TransformStep {
  id: number;
  ordinal: number;
  transformer: TransformTypeInfo;
  params: string;
  description: string;
}

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
  materialization: string;
  steps: TransformStep[];
}

interface StepForm {
  transformer: string;
  params: Record<string, string>;
  description: string;
}

interface TransformForm {
  source_duckdb_table: string;
  target_duckdb_table: string;
  description: string;
  materialization: string;
  steps: StepForm[];
}

interface TargetColumnMeta {
  name: string;
  db_type: string;
  nullable: boolean;
}

interface TargetMeta {
  columns: TargetColumnMeta[];
  primary_key: string[];
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

      /* -- Modal overlay -- */
      .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .modal-dialog {
        background: var(--shenas-bg, #fff);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 10px;
        padding: 1.5rem 2rem;
        width: 90vw;
        max-width: 960px;
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      .modal-dialog h2 {
        margin: 0;
        font-size: 1.1rem;
      }
      .modal-header-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }
      .modal-header-row label {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        font-size: 0.85rem;
      }
      .modal-header-row select,
      .modal-header-row input {
        padding: 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
      }

      /* -- Step rows -- */
      .step-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
      }
      .step-table th {
        text-align: left;
        padding: 0.3rem 0.5rem;
        font-weight: 600;
        color: var(--shenas-text-muted, #888);
        border-bottom: 1px solid var(--shenas-border, #e0e0e0);
        white-space: nowrap;
      }
      .step-table td {
        padding: 0.4rem 0.5rem;
        vertical-align: middle;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
      }
      .step-table select,
      .step-table input {
        padding: 0.3rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.8rem;
        width: 100%;
        box-sizing: border-box;
      }
      .step-table textarea {
        min-height: 60px;
        font-size: 0.8rem;
        padding: 0.3rem;
        width: 100%;
        box-sizing: border-box;
      }
      .step-num {
        color: var(--shenas-text-muted, #888);
        font-weight: 600;
        white-space: nowrap;
      }
      .step-params {
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem 0.8rem;
      }
      .step-params label {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        min-width: 120px;
        flex: 1;
      }
      .step-params label span {
        font-size: 0.75rem;
        color: var(--shenas-text-muted, #888);
      }
      .step-sql-row td {
        padding: 0.2rem 0.5rem 0.4rem;
      }
      .remove-step {
        background: none;
        border: 1px solid var(--shenas-border, #ddd);
        border-radius: 4px;
        color: #c00;
        cursor: pointer;
        padding: 0.2rem 0.5rem;
        font-size: 0.75rem;
      }
      .modal-footer {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        margin-top: 0.5rem;
      }
    `,
  ];

  declare apiBase: string;
  declare source: string;
  declare sourceTables: { table: string; display_name: string; schema?: string }[];
  declare targetTables: string[] | { table: string; display_name: string }[];
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
  declare _sourceColumnsFor: string;
  declare _targetColumns: string[];
  declare _targetColumnsFor: string;
  declare _categorySets: Array<{ displayName: string; values: Array<{ value: string }> }>;
  private _targetDisplayNames: Map<string, string> = new Map();
  private _targetMeta: TargetMeta | null = null;
  private _newTargetMode = false;
  private _newTargetDisplayName = "";

  private _client = getClient();

  private _transformsQuery = new ApolloQueryController(this, GET_TRANSFORMS, {
    client: this._client,
    noAutoSubscribe: true,
  });

  private _enableTransform = new ApolloMutationController(this, ENABLE_TRANSFORM, { client: this._client });
  private _disableTransform = new ApolloMutationController(this, DISABLE_TRANSFORM, { client: this._client });
  private _deleteTransform = new ApolloMutationController(this, DELETE_TRANSFORM, { client: this._client });
  private _updateTransform = new ApolloMutationController(this, UPDATE_TRANSFORM, { client: this._client });
  private _updateTransformSteps = new ApolloMutationController(this, UPDATE_TRANSFORM_STEPS, {
    client: this._client,
  });
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
    this._sourceColumnsFor = "";
    this._targetColumns = [];
    this._targetColumnsFor = "";
    this._categorySets = [];
  }

  _emptyForm(): TransformForm {
    return {
      source_duckdb_table: "",
      target_duckdb_table: "",
      description: "",
      materialization: "table",
      steps: [{ transformer: "sql", params: { mode: "builder" }, description: "" }],
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

  _typeInfoFor(name: string): TransformTypeInfo | undefined {
    return this._transformTypes.find((t) => t.name === name);
  }

  /** Columns available at a given step index (output of previous step, or source columns for step 0). */
  _columnsForStep(stepIndex: number): string[] {
    const baseCols = this._sourceColumns.filter((c) => !c.startsWith("_dlt_"));
    if (stepIndex === 0) return baseCols;

    // Start from the columns the previous step produces.
    let cols = baseCols;
    for (let prior = 0; prior < stepIndex; prior++) {
      const step = this._newForm.steps[prior];

      // SQL builder step: output is the selected columns (aliased names take precedence).
      if (step.transformer === "sql" && step.params["mode"] !== "raw") {
        const selected = (step.params["columns"] as unknown as Array<{ name: string; alias: string | null }>) || [];
        if (selected.length > 0) {
          cols = selected.map((c) => c.alias || c.name);
        }
      }

      // Append any output columns declared by the transformer (e.g. LLM categorize adds a column).
      const typeInfo = this._typeInfoFor(step.transformer);
      if (typeInfo) {
        for (const param of typeInfo.paramSchema) {
          if (param.role === "output_column") {
            const colName = step.params[param.name] || param.default || "";
            if (colName && !cols.includes(colName)) cols = [...cols, colName];
          }
        }
      }
    }
    return cols;
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

  _inspectTable(schema: string, table: string, displayName?: string): void {
    this.dispatchEvent(
      new CustomEvent("inspect-table", {
        bubbles: true,
        composed: true,
        detail: { schema, table, displayName },
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

  async _startEdit(t: Transform): Promise<void> {
    this._editing = t.id;
    this._editSql = t.sql;
    this._previewRows = null;

    // Populate the create modal form from the existing transform
    const steps: StepForm[] =
      t.steps && t.steps.length > 0
        ? t.steps.map((step) => {
            let params: Record<string, string> = {};
            try {
              params = JSON.parse(step.params);
            } catch {
              /* ignore */
            }
            return { transformer: step.transformer.name, params, description: step.description };
          })
        : [{ transformer: t.transformType, params: { mode: "builder" }, description: "" }];

    this._newForm = {
      source_duckdb_table: t.source.tableName,
      target_duckdb_table: t.target.tableName,
      description: t.description,
      materialization: (t as unknown as { materialization?: string }).materialization || "table",
      steps,
    };
    this._creating = true;
    this._sourceColumnsFor = "";
    this._targetColumnsFor = "";
    await Promise.all([this._ensureCategorySets(), this._ensureTargetDisplayNames()]);
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
    this._sourceColumnsFor = "";
    this._targetColumnsFor = "";
    this._editing = null;
    this._previewRows = null;
    await Promise.all([this._ensureCategorySets(), this._ensureTargetDisplayNames()]);
  }

  private async _ensureTargetDisplayNames(): Promise<void> {
    if (this._targetDisplayNames.size > 0) return;
    const { data } = await this._client.query({ query: GET_DATA_RESOURCES });
    for (const resource of (data?.dataResources || []) as Array<{
      tableName: string;
      displayName: string;
      schemaName: string;
    }>) {
      if (resource.schemaName === "datasets") {
        this._targetDisplayNames.set(resource.tableName, resource.displayName);
      }
    }
    this.requestUpdate();
  }

  _cancelCreate(): void {
    this._creating = false;
    this._editing = null;
    this._newForm = this._emptyForm();
    this._sourceColumnsFor = "";
    this._targetColumnsFor = "";
    this._targetMeta = null;
    this._newTargetMode = false;
    this._newTargetDisplayName = "";
  }

  async _onSourceTableChange(table: string): Promise<void> {
    this._newForm = { ...this._newForm, source_duckdb_table: table };
    this._sourceColumnsFor = table;
    const entry = (this.sourceTables || []).find((entry) => entry.table === table);
    const schema = entry?.schema || this.source;
    this._sourceColumns = await this._fetchColumns(schema, table);
    this.requestUpdate();
  }

  async _onTargetTableChange(table: string): Promise<void> {
    this._newForm = { ...this._newForm, target_duckdb_table: table };
    this._targetColumnsFor = table;
    this._targetColumns = await this._fetchColumns("datasets", table);
    // Fetch full target schema for compatibility validation
    try {
      const { data } = await this._client.query({
        query: GET_TABLE_METADATA,
        variables: { s: "datasets", t: table },
        fetchPolicy: "network-only",
      });
      const meta = data?.tableMetadata as Record<string, unknown> | null;
      if (meta) {
        this._targetMeta = {
          columns: (meta.columns as TargetColumnMeta[]) || [],
          primary_key: (meta.primary_key as string[]) || [],
        };
      } else {
        this._targetMeta = null;
      }
    } catch {
      this._targetMeta = null;
    }
    this.requestUpdate();
  }

  /** Compute output column names from all configured steps. */
  _outputColumns(): string[] {
    const lastStepIndex = this._newForm.steps.length - 1;
    return this._columnsForStep(lastStepIndex + 1);
  }

  /** Render compatibility indicator between transform output and target table. */
  _renderCompatibility() {
    if (!this._targetMeta || this._sourceColumns.length === 0) return "";
    const output = new Set(this._outputColumns());
    const targetCols = this._targetMeta.columns.map((c) => c.name);
    const pk = this._targetMeta.primary_key;

    const missingPK = pk.filter((col) => !output.has(col));
    const missingRequired = this._targetMeta.columns.filter(
      (c) => !c.nullable && !output.has(c.name) && !pk.includes(c.name),
    );
    const extraCols = [...output].filter((col) => !targetCols.includes(col) && !col.startsWith("_"));
    const matchedCols = targetCols.filter((col) => output.has(col));

    if (missingPK.length > 0 || missingRequired.length > 0) {
      const issues: string[] = [];
      if (missingPK.length > 0) issues.push(`Missing primary key: ${missingPK.join(", ")}`);
      if (missingRequired.length > 0) issues.push(`Missing required: ${missingRequired.map((c) => c.name).join(", ")}`);
      return html`<div style="font-size:0.8rem;color:var(--shenas-error,#c62828);margin-top:0.5rem">
        ${issues.join(". ")}. ${matchedCols.length}/${targetCols.length} target columns matched.
      </div>`;
    }
    if (extraCols.length > 0) {
      return html`<div style="font-size:0.8rem;color:#f57c00;margin-top:0.5rem">
        ${matchedCols.length}/${targetCols.length} target columns matched. ${extraCols.length} extra
        column${extraCols.length > 1 ? "s" : ""} will be ignored: ${extraCols.join(", ")}
      </div>`;
    }
    return html`<div style="font-size:0.8rem;color:var(--shenas-success,#628261);margin-top:0.5rem">
      ${matchedCols.length}/${targetCols.length} target columns matched.
    </div>`;
  }

  _addStep(): void {
    this._newForm = {
      ...this._newForm,
      steps: [...this._newForm.steps, { transformer: "sql", params: {}, description: "" }],
    };
  }

  _removeStep(index: number): void {
    if (this._newForm.steps.length <= 1) return;
    const steps = [...this._newForm.steps];
    steps.splice(index, 1);
    this._newForm = { ...this._newForm, steps };
  }

  _updateStepType(index: number, transformer: string): void {
    const steps = [...this._newForm.steps];
    steps[index] = { ...steps[index], transformer, params: {} };
    this._newForm = { ...this._newForm, steps };
  }

  _updateStepParam(index: number, paramName: string, value: string): void {
    const steps = [...this._newForm.steps];
    steps[index] = { ...steps[index], params: { ...steps[index].params, [paramName]: value } };
    this._newForm = { ...this._newForm, steps };
  }

  async _saveCreate(): Promise<void> {
    const f = this._newForm;
    if (!f.source_duckdb_table || !f.target_duckdb_table) {
      this._message = { type: "error", text: "Source and target tables are required" };
      return;
    }
    if (f.steps.length === 0) {
      this._message = { type: "error", text: "At least one step is required" };
      return;
    }

    const steps = f.steps.map((step) => ({
      transformer: step.transformer,
      params: JSON.stringify(step.params),
      description: step.description,
    }));

    try {
      if (this._editing) {
        // Update existing transform's steps
        await this._updateTransformSteps.mutate({
          variables: { transformId: this._editing, steps },
        });
        this._message = { type: "success", text: "Transform updated" };
      } else {
        await this._createTransform.mutate({
          variables: {
            input: {
              sourceDuckdbSchema:
                (this.sourceTables || []).find((entry) => entry.table === f.source_duckdb_table)?.schema || this.source,
              sourceDuckdbTable: f.source_duckdb_table,
              targetDuckdbSchema: "datasets",
              targetDuckdbTable: f.target_duckdb_table,
              sourcePlugin: this.source,
              description: f.description,
              materialization: f.materialization,
              steps,
              transformType: f.steps[0].transformer,
              params: JSON.stringify(f.steps[0].params),
            },
          },
        });
        this._message = { type: "success", text: "Transform created" };
      }
      this._creating = false;
      this._editing = null;
      this._newForm = this._emptyForm();
      await this._fetchAll();
    } catch {
      this._message = { type: "error", text: this._editing ? "Update failed" : "Create failed" };
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

  _stepsDescription(t: Transform): string {
    const steps = t.steps || [];
    if (steps.length <= 1) {
      return steps[0]?.transformer.displayName || t.transformType;
    }
    return steps.map((s) => s.transformer.displayName || s.transformer.name).join(" \u2192 ");
  }

  // -- Rendering ----------------------------------------------------------

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
                  style="cursor:pointer;text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                  title="${t.source.schemaName}.${t.source.tableName}"
                  @click=${() => this._inspectTable(t.source.schemaName, t.source.tableName, t.source.displayName)}
                  >${t.source.displayName || t.source.tableName}</span
                >`,
            },
            {
              label: "Target",
              render: (t: Transform) =>
                html`<span
                  style="cursor:pointer;text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                  title="${t.target.schemaName}.${t.target.tableName}"
                  @click=${() => this._inspectTable(t.target.schemaName, t.target.tableName, t.target.displayName)}
                  >${t.target.displayName || t.target.tableName}</span
                >`,
            },
            {
              label: "Pipeline",
              render: (t: Transform) => html`<span style="font-size:0.85rem">${this._stepsDescription(t)}</span>`,
            },
            {
              label: "Description",
              render: (t: Transform) =>
                html`${t.description || ""}${t.isDefault
                  ? html`<shenas-badge variant="muted">default</shenas-badge>`
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
      ${this._creating ? this._renderCreateModal() : ""}
    `;
  }

  // -- Create modal -------------------------------------------------------

  _renderCreateModal() {
    const f = this._newForm;
    const sourceTableEntries = (this.sourceTables || []).map((entry) => ({
      value: entry.table,
      label: entry.display_name || entry.table,
    }));
    const targetTableEntries = (this.targetTables || []).map((entry) => {
      if (typeof entry === "string") {
        return { value: entry, label: this._targetDisplayNames.get(entry) || entry };
      }
      return { value: entry.table, label: entry.display_name || entry.table };
    });

    // Kick off column fetch if table is selected but not yet fetched
    if (f.source_duckdb_table && this._sourceColumnsFor !== f.source_duckdb_table) {
      this._onSourceTableChange(f.source_duckdb_table);
    }
    if (f.target_duckdb_table && !this._newTargetMode && this._targetColumnsFor !== f.target_duckdb_table) {
      this._onTargetTableChange(f.target_duckdb_table);
    }

    return html`
      <div
        class="modal-backdrop"
        @click=${(e: Event) => {
          if (e.target === e.currentTarget) this._cancelCreate();
        }}
      >
        <div class="modal-dialog">
          <h2>${this._editing ? "Edit transform" : "New transform"}</h2>

          <div class="modal-header-row">
            <label>
              Source table
              <select
                ?disabled=${!!this._editing}
                @change=${(e: Event) => this._onSourceTableChange((e.target as HTMLSelectElement).value)}
              >
                <option value="">-- select --</option>
                ${sourceTableEntries.map(
                  (entry) =>
                    html`<option value=${entry.value} ?selected=${f.source_duckdb_table === entry.value}>
                      ${entry.label}
                    </option>`,
                )}
              </select>
            </label>
            <label>
              Target table
              ${this._newTargetMode
                ? html`<input
                    type="text"
                    placeholder="e.g. Daily Downloads"
                    .value=${this._newTargetDisplayName}
                    @input=${(e: InputEvent) => {
                      this._newTargetDisplayName = (e.target as HTMLInputElement).value;
                      const slug = this._newTargetDisplayName
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, "_")
                        .replace(/^_|_$/g, "");
                      const tableName = slug ? `custom__${slug}` : "";
                      this._newForm = { ...this._newForm, target_duckdb_table: tableName };
                    }}
                  />`
                : html`<select
                    ?disabled=${!!this._editing}
                    @change=${(e: Event) => {
                      const val = (e.target as HTMLSelectElement).value;
                      if (val === "__new__") {
                        this._newTargetMode = true;
                        this._newTargetDisplayName = "";
                        this._newForm = { ...this._newForm, target_duckdb_table: "" };
                        this._targetMeta = null;
                        this.requestUpdate();
                      } else {
                        this._onTargetTableChange(val);
                      }
                    }}
                  >
                    <option value="">-- select --</option>
                    ${targetTableEntries.map(
                      (entry) =>
                        html`<option value=${entry.value} ?selected=${f.target_duckdb_table === entry.value}>
                          ${entry.label}
                        </option>`,
                    )}
                    ${!this._editing ? html`<option value="__new__">+ New table...</option>` : ""}
                  </select>`}
            </label>
          </div>

          <div style="font-weight:600;font-size:0.9rem">Steps</div>

          <table class="step-table">
            <thead>
              <tr>
                <th></th>
                <th>Type</th>
                <th>Parameters</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${f.steps.map((step, idx) => this._renderStepRow(step, idx))}
            </tbody>
          </table>

          <button @click=${this._addStep} style="align-self:flex-start">+ Add step</button>

          ${this._renderCompatibility()}

          <div style="display:flex;gap:1rem;align-items:center;font-size:0.85rem">
            <span>Output as</span>
            <label style="display:flex;align-items:center;gap:0.3rem">
              <input
                type="radio"
                name="materialization"
                value="table"
                ?checked=${f.materialization === "table"}
                ?disabled=${!!this._editing}
                @change=${() => {
                  this._newForm = { ...this._newForm, materialization: "table" };
                }}
              />
              Table
            </label>
            <label style="display:flex;align-items:center;gap:0.3rem">
              <input
                type="radio"
                name="materialization"
                value="view"
                ?checked=${f.materialization === "view"}
                ?disabled=${!!this._editing}
                @change=${() => {
                  this._newForm = { ...this._newForm, materialization: "view" };
                }}
              />
              View
            </label>
          </div>

          <label style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.85rem">
            Description
            <input
              .value=${f.description}
              @input=${(e: InputEvent) => {
                this._newForm = { ...this._newForm, description: (e.target as HTMLInputElement).value };
              }}
            />
          </label>

          <div class="modal-footer">
            <button @click=${this._saveCreate}>${this._editing ? "Save" : "Create"}</button>
            <button @click=${this._cancelCreate}>Cancel</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderStepRow(step: StepForm, index: number) {
    const types = this._transformTypes;
    const typeInfo = this._typeInfoFor(step.transformer);
    const paramFields = typeInfo?.paramSchema || [];
    const inlineParams = paramFields.filter((p) => p.type !== "textarea" && p.name !== "mode");
    const textareaParams = paramFields.filter((p) => p.type === "textarea");
    const availableCols = this._columnsForStep(index);

    const renderInlineParam = (p: ParamField) => {
      if (p.visible_when) {
        const hidden = Object.entries(p.visible_when).some(([k, v]) => (step.params[k] || "") !== v);
        if (hidden) return "";
      }
      const val = step.params[p.name] || p.default || "";

      if (p.type === "source_column") {
        return html`<label>
          <span>${p.label}${p.required ? " *" : ""}</span>
          <select @change=${(e: Event) => this._updateStepParam(index, p.name, (e.target as HTMLSelectElement).value)}>
            <option value="">--</option>
            ${availableCols.map((c) => html`<option value=${c} ?selected=${val === c}>${c}</option>`)}
          </select>
        </label>`;
      }
      if (p.type === "target_column") {
        const tgtCols = this._targetColumns.filter((c) => !c.startsWith("_dlt_"));
        return html`<label>
          <span>${p.label}${p.required ? " *" : ""}</span>
          <select @change=${(e: Event) => this._updateStepParam(index, p.name, (e.target as HTMLSelectElement).value)}>
            <option value="">--</option>
            ${tgtCols.map((c) => html`<option value=${c} ?selected=${val === c}>${c}</option>`)}
          </select>
        </label>`;
      }
      if (p.type === "category_set") {
        return html`<label>
          <span>${p.label}</span>
          <select @change=${(e: Event) => this._updateStepParam(index, p.name, (e.target as HTMLSelectElement).value)}>
            <option value="">--</option>
            ${(this._categorySets || []).map(
              (s) =>
                html`<option
                  value=${s.values.map((v) => v.value).join(",")}
                  ?selected=${val === s.values.map((v) => v.value).join(",")}
                >
                  ${s.displayName}
                </option>`,
            )}
          </select>
        </label>`;
      }
      if (p.type === "select" && p.options) {
        return html`<label>
          <span>${p.label}</span>
          <select @change=${(e: Event) => this._updateStepParam(index, p.name, (e.target as HTMLSelectElement).value)}>
            ${p.options.map((o) => html`<option value=${o} ?selected=${val === o}>${o}</option>`)}
          </select>
        </label>`;
      }
      return html`<label>
        <span>${p.label}${p.required ? " *" : ""}</span>
        <input
          .value=${val}
          @input=${(e: InputEvent) => this._updateStepParam(index, p.name, (e.target as HTMLInputElement).value)}
          type=${p.type === "number" ? "number" : "text"}
        />
      </label>`;
    };

    return html`
      <tr>
        <td class="step-num">${index + 1}</td>
        <td style="min-width:140px">
          <select @change=${(e: Event) => this._updateStepType(index, (e.target as HTMLSelectElement).value)}>
            ${types.map(
              (t) => html`<option value=${t.name} ?selected=${step.transformer === t.name}>${t.displayName}</option>`,
            )}
          </select>
        </td>
        <td>
          <div class="step-params">${inlineParams.map(renderInlineParam)}</div>
        </td>
        <td>
          ${this._newForm.steps.length > 1
            ? html`<button class="remove-step" @click=${() => this._removeStep(index)}>Remove</button>`
            : ""}
        </td>
      </tr>
      ${this._renderStepExpanded(step, index, textareaParams, availableCols)}
    `;
  }

  _renderStepExpanded(step: StepForm, index: number, textareaParams: ParamField[], availableCols: string[]) {
    // SQL transformer in builder mode: render <sql-builder>
    const mode = step.params["mode"] || "builder";
    if (step.transformer === "sql" && mode === "builder") {
      const builderValue = {
        columns: (step.params["columns"] as unknown as Array<Record<string, string | null>>) || [],
        filters: (step.params["filters"] as unknown as Array<Record<string, string | null>>) || [],
        group_by: (step.params["group_by"] as unknown as string[]) || [],
        order_by: (step.params["order_by"] as unknown as Array<Record<string, string>>) || [],
        limit: step.params["limit"] != null ? Number(step.params["limit"]) : null,
      };
      return html`
        <tr class="step-sql-row">
          <td></td>
          <td colspan="3">
            <sql-builder
              .columns=${availableCols}
              .value=${builderValue}
              @change=${(e: CustomEvent) => {
                const query = e.detail;
                const steps = [...this._newForm.steps];
                steps[index] = {
                  ...steps[index],
                  params: { ...steps[index].params, ...query },
                };
                this._newForm = { ...this._newForm, steps };
              }}
            ></sql-builder>
          </td>
        </tr>
      `;
    }

    // Raw SQL or other textarea params
    return textareaParams.map(
      (p) => html`
        <tr class="step-sql-row">
          <td></td>
          <td colspan="3">
            <textarea
              placeholder="${p.label}${p.required ? " *" : ""}"
              .value=${step.params[p.name] || p.default || ""}
              @input=${(e: InputEvent) => this._updateStepParam(index, p.name, (e.target as HTMLTextAreaElement).value)}
            ></textarea>
          </td>
        </tr>
      `,
    );
  }

  // -- View panel ---------------------------------------------------------

  _openViewPanel(t: Transform): void {
    const panel = document.createElement("div");
    panel.style.padding = "1rem";

    const stepsHtml = (t.steps || [])
      .map(
        (step, idx) => `
      <div style="padding:0.5rem;border:1px solid var(--shenas-border-light,#eee);border-radius:4px;margin-bottom:0.4rem">
        <div style="font-weight:600;font-size:0.85rem;margin-bottom:0.3rem">
          <span style="color:var(--shenas-text-muted,#888);font-weight:normal">Step ${idx + 1}:</span>
          ${step.transformer.displayName || step.transformer.name}
        </div>
        ${step.description ? `<div style="font-size:0.8rem;color:var(--shenas-text-secondary,#666);margin-bottom:0.2rem">${step.description}</div>` : ""}
        ${Object.entries(JSON.parse(step.params || "{}"))
          .filter(([k]) => k !== "sql")
          .map(
            ([k, v]) =>
              `<div style="font-size:0.8rem"><span style="color:var(--shenas-text-muted,#888)">${k}:</span> ${v}</div>`,
          )
          .join("")}
        ${(() => {
          const p = JSON.parse(step.params || "{}");
          return p.sql
            ? `<textarea readonly style="padding:0.4rem;border:1px solid var(--shenas-border-light,#eee);border-radius:4px;background:var(--shenas-bg-hover,#f5f5f5);font-family:monospace;resize:vertical;min-height:4rem;width:100%;box-sizing:border-box;white-space:pre;overflow:auto;margin-top:0.3rem;font-size:0.8rem">${p.sql}</textarea>`
            : "";
        })()}
      </div>`,
      )
      .join("");

    panel.innerHTML = `
      <h3 style="margin:0 0 1rem;font-size:1rem">
        ${t.source.displayName || t.source.tableName} \u2192 ${t.target.displayName || t.target.tableName}
      </h3>
      <div style="display:flex;flex-direction:column;gap:0.4rem">
        ${t.description ? `<div style="font-size:0.85rem;margin-bottom:0.5rem">${t.description}</div>` : ""}
        ${stepsHtml}
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

  // -- Edit panel ---------------------------------------------------------

  _renderEditor() {
    const t = this._transforms.find((x) => x.id === this._editing);
    if (!t) return "";
    const readonly = t.isDefault;
    return html`
      <div class="edit-panel">
        <h3>
          ${readonly ? "View" : "Edit"}: ${t.source.displayName || t.source.tableName} →
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
