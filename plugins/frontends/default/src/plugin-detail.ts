import { LitElement, html, css } from "lit";
import {
  gql,
  gqlFull,
  registerCommands,
  renderMessage,
  buttonStyles,
  linkStyles,
  messageStyles,
  tabStyles,
} from "shenas-frontends";

interface TableInfo {
  name: string;
  rows?: number;
  cols?: number;
  earliest?: string;
  latest?: string;
}

class PluginDetail extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    activeTab: { type: String, attribute: "active-tab" },
    dbStatus: { type: Object },
    schemaPlugins: { type: Object },
    initialInfo: { type: Object },
    _info: { state: true },
    _loading: { state: true },
    _showLoading: { state: true },
    _message: { state: true },
    _tables: { state: true },
    _syncing: { state: true },
    _transforming: { state: true },
    _schemaTransforms: { state: true },
    _selectedTable: { state: true },
    _previewRows: { state: true },
    _previewLoading: { state: true },
  };

  static styles = [
    buttonStyles,
    linkStyles,
    messageStyles,
    tabStyles,
    css`
      :host {
        display: block;
        color: var(--text-color);
        background: var(--bg-color);
      }

      .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;
      }

      .header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-color);
      }

      .plugin-icon {
        font-size: 2rem;
      }

      .plugin-info {
        flex: 1;
      }

      .plugin-name {
        font-size: 1.5rem;
        font-weight: 600;
      }

      .plugin-kind {
        font-size: 0.875rem;
        color: var(--text-secondary);
        text-transform: capitalize;
      }

      .plugin-version {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-left: 0.5rem;
      }

      .plugin-description {
        margin-top: 0.5rem;
        font-size: 0.95rem;
        color: var(--text-secondary);
      }

      .header-actions {
        display: flex;
        gap: 0.5rem;
      }

      .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 0.5rem;
      }

      .status-indicator.enabled {
        background-color: #4ade80;
      }

      .status-indicator.disabled {
        background-color: #ef4444;
      }

      .status-indicator.error {
        background-color: #f59e0b;
      }

      .tabs {
        display: flex;
        gap: 0;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 1.5rem;
      }

      .tab {
        padding: 0.75rem 1rem;
        border: none;
        background: none;
        color: var(--text-secondary);
        cursor: pointer;
        font-size: 0.95rem;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
      }

      .tab.active {
        color: var(--text-color);
        border-bottom-color: var(--accent-color);
      }

      .tab:hover {
        color: var(--text-color);
      }

      .tab-content {
        animation: fadeIn 0.2s ease-in;
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
        }
        to {
          opacity: 1;
        }
      }

      .sync-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background: var(--bg-secondary);
        border-left: 4px solid var(--accent-color);
      }

      .sync-status.error {
        background: rgba(239, 68, 68, 0.1);
        border-left-color: #ef4444;
      }

      .table-list {
        display: grid;
        gap: 0.75rem;
      }

      .table-item {
        padding: 0.75rem;
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .table-item:hover {
        background: var(--bg-secondary);
        border-color: var(--accent-color);
      }

      .table-item.selected {
        background: var(--bg-secondary);
        border-color: var(--accent-color);
      }

      .table-name {
        font-weight: 500;
        margin-bottom: 0.25rem;
      }

      .table-stats {
        display: flex;
        gap: 1rem;
        font-size: 0.85rem;
        color: var(--text-secondary);
      }

      .table-stat {
        display: flex;
        align-items: center;
        gap: 0.25rem;
      }

      .preview {
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        overflow: hidden;
      }

      .preview-loading {
        padding: 2rem;
        text-align: center;
        color: var(--text-secondary);
      }

      .preview-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
      }

      .preview-table thead {
        background: var(--bg-secondary);
        border-bottom: 1px solid var(--border-color);
      }

      .preview-table th,
      .preview-table td {
        padding: 0.5rem;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
      }

      .preview-table tbody tr:hover {
        background: var(--bg-secondary);
      }

      .transform-list {
        display: grid;
        gap: 0.75rem;
      }

      .transform-item {
        padding: 0.75rem;
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
      }

      .transform-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
      }

      .transform-name {
        font-weight: 500;
      }

      .transform-path {
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-family: monospace;
      }

      .transform-description {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
      }

      .transform-toggle {
        font-size: 0.85rem;
      }

      .empty-state {
        padding: 2rem;
        text-align: center;
        color: var(--text-secondary);
      }

      .config-form {
        display: grid;
        gap: 1rem;
      }

      .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }

      .form-label {
        font-weight: 500;
        font-size: 0.95rem;
      }

      .form-input {
        padding: 0.5rem;
        border: 1px solid var(--border-color);
        border-radius: 0.375rem;
        font-size: 0.95rem;
        background: var(--bg-color);
        color: var(--text-color);
      }

      .form-input:focus {
        outline: none;
        border-color: var(--accent-color);
      }

      .form-help {
        font-size: 0.85rem;
        color: var(--text-secondary);
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "http://localhost:3000";
    this.kind = "source";
    this.name = "";
    this.activeTab = "overview";
    this.dbStatus = {};
    this.schemaPlugins = {};
    this.initialInfo = {};
    this._info = null;
    this._loading = false;
    this._showLoading = false;
    this._message = null;
    this._tables = [];
    this._syncing = false;
    this._transforming = false;
    this._schemaTransforms = [];
    this._selectedTable = null;
    this._previewRows = [];
    this._previewLoading = false;
  }

  declare apiBase: string;
  declare kind: string;
  declare name: string;
  declare activeTab: string;
  declare dbStatus: Record<string, unknown>;
  declare schemaPlugins: Record<string, unknown>;
  declare initialInfo: Record<string, unknown>;
  declare _info: Record<string, unknown> | null;
  declare _loading: boolean;
  declare _showLoading: boolean;
  declare _message: { type: string; text: string } | null;
  declare _tables: TableInfo[];
  declare _syncing: boolean;
  declare _transforming: boolean;
  declare _schemaTransforms: Record<string, unknown>[];
  declare _selectedTable: TableInfo | null;
  declare _previewRows: Record<string, unknown>[];
  declare _previewLoading: boolean;

  connectedCallback() {
    super.connectedCallback();
    this._loadPluginInfo();
    registerCommands(this, "plugin-detail", [{ command: "refresh", action: () => this._loadPluginInfo() }]);
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has("name") || changedProperties.has("kind")) {
      this._loadPluginInfo();
    }
  }

  private async _loadPluginInfo() {
    this._loading = true;
    try {
      const response = (await gql(
        this.apiBase,
        `query($name: String!, $kind: String!) { pluginInfo(kind: $kind, name: $name) }`,
        {
          name: this.name,
          kind: this.kind,
        },
      )) as { pluginInfo?: Record<string, unknown> } | null;

      if (response?.pluginInfo) {
        this._info = response.pluginInfo;
        this._loadTables();
        this._loadSchemaTransforms();
      }
    } catch (error) {
      this._message = {
        type: "error",
        text: `Failed to load plugin info: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      this._loading = false;
    }
  }

  private async _loadTables() {
    try {
      const schema = `${this.name.replace(/[^a-z0-9_]/gi, "_")}`;
      const response = await gql(
        this.apiBase,
        `query { dbStatus { schemas { name tables { name rows cols earliest latest } } } }`,
      );

      const data = response as { dbStatus?: { schemas?: Array<{ name: string; tables: TableInfo[] }> } } | null;
      const schemas = data?.dbStatus?.schemas || [];
      const schema_data = schemas.find((s: { name: string }) => s.name === schema);
      this._tables = schema_data?.tables || [];
    } catch (error) {
      console.error("Failed to load tables:", error);
    }
  }

  private async _loadSchemaTransforms() {
    try {
      const response = await gql(
        this.apiBase,
        `query($source: String) { transforms(source: $source) { id transformType source { id schemaName tableName } target { id schemaName tableName } sourcePlugin description enabled } }`,
        { source: this.name },
      );
      const data = response as { transforms?: Record<string, unknown>[] } | null;
      this._schemaTransforms = data?.transforms || [];
    } catch (error) {
      console.error("Failed to load schema transforms:", error);
    }
  }

  private async _syncPlugin() {
    this._syncing = true;
    this._message = null;
    try {
      const response = await gqlFull(
        this.apiBase,
        `mutation { syncPlugin(name: "${this.name}", kind: "${this.kind}") { success message synced_at } }`,
      );

      const result = response as { data?: { syncPlugin?: { success: boolean; message?: string } } };
      if (result.data?.syncPlugin?.success) {
        this._message = {
          type: "success",
          text: result.data.syncPlugin.message || "Plugin synced successfully",
        };
        this._loadPluginInfo();
      } else {
        this._message = {
          type: "error",
          text: result.data?.syncPlugin?.message || "Sync failed",
        };
      }
    } catch (error) {
      this._message = {
        type: "error",
        text: `Sync failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      this._syncing = false;
    }
  }

  private async _toggleTransform(transformId: number, enabled: boolean) {
    this._transforming = true;
    try {
      const response = await gqlFull(
        this.apiBase,
        `mutation { updateTransform(id: ${transformId}, enabled: ${!enabled}) { id enabled } }`,
      );

      const result = response as { data?: { updateTransform?: unknown } };
      if (result.data?.updateTransform) {
        this._loadSchemaTransforms();
      }
    } catch (error) {
      this._message = {
        type: "error",
        text: `Failed to update transform: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      this._transforming = false;
    }
  }

  private _selectTable(table: TableInfo) {
    this._selectedTable = table;
    this._previewRows = [];
    this._previewLoading = true;

    // Simulate preview loading
    setTimeout(() => {
      this._previewLoading = false;
      // In real implementation, fetch preview from API
    }, 500);
  }

  render() {
    if (this._loading) {
      return html`
        <div class="container">
          <div class="empty-state">Loading plugin information...</div>
        </div>
      `;
    }

    if (!this._info) {
      return html`
        <div class="container">
          <div class="empty-state">Plugin not found</div>
        </div>
      `;
    }

    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- guarded by null check above
    const info = this._info!;
    return html`
      <div class="container">
        ${this._message ? renderMessage(this._message) : ""}

        <div class="header">
          <div class="plugin-icon">📦</div>
          <div class="plugin-info">
            <div class="plugin-name">${info.display_name || info.name}</div>
            <div>
              <span class="plugin-kind">${info.kind}</span>
              ${info.version ? html`<span class="plugin-version">v${info.version}</span>` : ""}
            </div>
            ${info.description ? html`<div class="plugin-description">${info.description}</div>` : ""}
          </div>
          <div class="header-actions">
            ${info.enabled
              ? html`<span class="status-indicator enabled" title="Enabled"></span>`
              : html`<span class="status-indicator disabled" title="Disabled"></span>`}
            <button ?disabled=${this._syncing} @click=${() => this._syncPlugin()} class="btn-primary">
              ${this._syncing ? "Syncing..." : "Sync Now"}
            </button>
          </div>
        </div>

        <div class="tabs">
          <button
            class="tab ${this.activeTab === "overview" ? "active" : ""}"
            @click=${() => (this.activeTab = "overview")}
          >
            Overview
          </button>
          <button
            class="tab ${this.activeTab === "tables" ? "active" : ""}"
            @click=${() => (this.activeTab = "tables")}
          >
            Tables
          </button>
          <button
            class="tab ${this.activeTab === "transforms" ? "active" : ""}"
            @click=${() => (this.activeTab = "transforms")}
          >
            Transforms
          </button>
          ${info.has_config || info.has_auth
            ? html`
                <button
                  class="tab ${this.activeTab === "config" ? "active" : ""}"
                  @click=${() => (this.activeTab = "config")}
                >
                  Config
                </button>
              `
            : ""}
        </div>

        <div class="tab-content">
          ${this.activeTab === "overview" ? this._renderOverview() : ""}
          ${this.activeTab === "tables" ? this._renderTables() : ""}
          ${this.activeTab === "transforms" ? this._renderTransforms() : ""}
          ${this.activeTab === "config" ? this._renderConfig() : ""}
        </div>
      </div>
    `;
  }

  private _renderOverview() {
    return html`
      <div>
        <h3>Plugin Information</h3>
        <div class="sync-status">
          ${this._info!.synced_at
            ? html`<p>Last synced: ${new Date(this._info!.synced_at as string).toLocaleString()}</p>`
            : html`<p>Never synced</p>`}
          ${this._info!.updated_at
            ? html`<p>Last updated: ${new Date(this._info!.updated_at as string).toLocaleString()}</p>`
            : ""}
        </div>
        <div class="config-form">
          <div class="form-group">
            <label class="form-label">Status</label>
            <div>${this._info!.enabled ? "Enabled" : "Disabled"}</div>
          </div>
          ${this._info!.has_data
            ? html`
                <div class="form-group">
                  <label class="form-label">Primary Table</label>
                  <div>${this._info!.primary_table || "N/A"}</div>
                </div>
              `
            : ""}
        </div>
      </div>
    `;
  }

  private _renderTables() {
    if (this._tables.length === 0) {
      return html`<div class="empty-state">No tables found</div>`;
    }

    return html`
      <div>
        <h3>Schema Tables</h3>
        <div class="table-list">
          ${this._tables.map(
            (table) => html`
              <div
                class="table-item ${this._selectedTable?.name === table.name ? "selected" : ""}"
                @click=${() => this._selectTable(table)}
              >
                <div class="table-name">${table.name}</div>
                <div class="table-stats">
                  ${table.rows ? html`<div class="table-stat"><span>Rows:</span> ${table.rows}</div>` : ""}
                  ${table.cols ? html`<div class="table-stat"><span>Columns:</span> ${table.cols}</div>` : ""}
                </div>
              </div>
            `,
          )}
        </div>
        ${this._selectedTable
          ? html`
              <h4 style="margin-top: 1.5rem">Preview: ${this._selectedTable.name}</h4>
              <div class="preview">
                ${this._previewLoading
                  ? html`<div class="preview-loading">Loading preview...</div>`
                  : html`
                      <table class="preview-table">
                        <thead>
                          <tr>
                            <th>Column Name</th>
                          </tr>
                        </thead>
                        <tbody>
                          ${this._previewRows.map(
                            (row) =>
                              html`<tr>
                                <td>${row}</td>
                              </tr>`,
                          )}
                        </tbody>
                      </table>
                    `}
              </div>
            `
          : ""}
      </div>
    `;
  }

  private _renderTransforms() {
    if (this._schemaTransforms.length === 0) {
      return html`<div class="empty-state">No transforms configured</div>`;
    }

    return html`
      <div>
        <h3>Schema Transforms</h3>
        <div class="transform-list">
          ${this._schemaTransforms.map(
            (transform) => html`
              <div class="transform-item">
                <div class="transform-header">
                  <div class="transform-name">Transform #${transform.id}</div>
                  <label class="transform-toggle">
                    <input
                      type="checkbox"
                      ?checked=${transform.enabled}
                      @change=${() => this._toggleTransform(transform.id as number, transform.enabled as boolean)}
                    />
                    ${transform.enabled ? "Enabled" : "Disabled"}
                  </label>
                </div>
                <div class="transform-path">
                  ${(transform.source as Record<string, string>)?.schemaName}.${(
                    transform.source as Record<string, string>
                  )?.tableName}
                  →
                  ${(transform.target as Record<string, string>)?.schemaName}.${(
                    transform.target as Record<string, string>
                  )?.tableName}
                </div>
                ${transform.description ? html`<div class="transform-description">${transform.description}</div>` : ""}
              </div>
            `,
          )}
        </div>
      </div>
    `;
  }

  private _renderConfig() {
    return html`
      <div>
        <h3>Configuration</h3>
        <div class="config-form">
          ${this._info!.has_auth
            ? html`<div class="form-group"><label class="form-label">Authentication</label></div>`
            : ""}
          ${this._info!.has_config
            ? html`<div class="form-group"><label class="form-label">Settings</label></div>`
            : ""}
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-plugin-detail", PluginDetail);
export { PluginDetail };
