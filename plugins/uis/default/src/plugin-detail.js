import { LitElement, html, css } from "lit";
import { arrowQuery, gql, gqlFull, registerCommands, renderMessage } from "./api.js";
import { buttonStyles, linkStyles, messageStyles, tabStyles } from "./shared-styles.js";

class PluginDetail extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    activeTab: { type: String, attribute: "active-tab" },
    dbStatus: { type: Object },
    schemaPlugins: { type: Object },
    _info: { state: true },
    _loading: { state: true },
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
      }
      .back {
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
      }
      .title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .title-actions {
        display: flex;
        gap: 0.5rem;
      }
      h2 {
        margin: 0;
        font-size: 1.3rem;
      }
      .kind-badge {
        background: var(--shenas-border-light, #f0f0f0);
        color: var(--shenas-text-secondary, #666);
        padding: 0.15rem 0.5rem;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 400;
        vertical-align: middle;
        margin-left: 0.3rem;
      }
      .version {
        color: var(--shenas-text-muted, #999);
        font-size: 0.7rem;
        font-weight: 400;
        vertical-align: middle;
      }
      .description {
        color: var(--shenas-text-secondary, #666);
        line-height: 1.6;
        margin: 1rem 0;
        white-space: pre-line;
      }
      .state-table {
        margin: 1.5rem 0;
      }
      .state-row {
        display: flex;
        padding: 0.4rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.9rem;
      }
      .state-row:last-child {
        border-bottom: none;
      }
      .state-label {
        width: 120px;
        color: var(--shenas-text-muted, #888);
        flex-shrink: 0;
      }
      .state-value {
        color: var(--shenas-text, #222);
      }
      button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
      .section-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        color: var(--shenas-text-muted, #888);
        letter-spacing: 0.05em;
        margin: 1.5rem 0 0.5rem;
      }
      .data-toolbar {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 1rem 0;
      }
      .data-toolbar select {
        padding: 0.4rem 0.6rem;
        font-size: 0.9rem;
        border: 1px solid var(--shenas-border, #ccc);
        border-radius: 4px;
      }
      .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
        margin-top: 0.5rem;
        overflow-x: auto;
        display: block;
      }
      .data-table th, .data-table td {
        padding: 0.35rem 0.6rem;
        border: 1px solid var(--shenas-border-light, #e8e8e8);
        text-align: left;
        white-space: nowrap;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .data-table th {
        background: var(--shenas-bg-secondary, #f5f5f5);
        font-weight: 600;
        position: sticky;
        top: 0;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this.activeTab = "details";
    this._info = null;
    this._loading = true;
    this._message = null;
    this._tables = [];
    this._syncing = false;
    this._schemaTransforms = [];
    this._selectedTable = null;
    this._previewRows = null;
    this._previewLoading = false;
  }

  willUpdate(changed) {
    if (changed.has("kind") || changed.has("name")) {
      this._fetchInfo();
    }
  }

  async _fetchInfo() {
    if (!this.kind || !this.name) return;
    this._loading = true;
    this._message = null;
    const needsSchema = this.kind === "schema";
    const fields = [
      `pluginInfo(kind: $kind, name: $name)`,
      needsSchema ? `transforms { id sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable sourcePlugin description enabled }` : "",
    ].filter(Boolean).join(" ");
    const data = await gql(this.apiBase, `query($kind: String!, $name: String!) { ${fields} }`, { kind: this.kind, name: this.name });
    this._info = data?.pluginInfo;
    const db = this.dbStatus;
    const ownership = this.schemaPlugins;
    const allTransforms = data?.transforms;
    const ownedTables = ownership ? (ownership[this.name] || []) : [];
    if (db) {
      if (this.kind === "pipe") {
        const schema = (db.schemas || []).find((s) => s.name === this.name);
        this._tables = schema ? schema.tables.filter((t) => !t.name.startsWith("_dlt_")) : [];
      } else if (this.kind === "schema") {
        const metricsSchema = (db.schemas || []).find((s) => s.name === "metrics");
        this._tables = metricsSchema
          ? metricsSchema.tables.filter((t) => ownedTables.includes(t.name))
          : [];
      }
    }
    if (allTransforms) {
      this._schemaTransforms = allTransforms.filter(
        (t) => ownedTables.includes(t.targetDuckdbTable),
      );
    }
    this._loading = false;
    this._registerCommands();
  }

  _registerCommands() {
    if (!this._info) return;
    const label = this._info.display_name || this.name;
    const cmds = [
      { id: `remove:${this.kind}:${this.name}`, category: "Plugin", label: `Remove ${label}`, action: () => this._remove() },
    ];
    if (this.kind === "schema") {
      cmds.unshift(
        { id: `flush:${this.kind}:${this.name}`, category: "Plugin", label: `Flush ${label}`, action: () => this._flush() },
        { id: `transform:${this.kind}:${this.name}`, category: "Plugin", label: `Transform ${label}`, action: () => this._runTransforms() },
      );
    }
    registerCommands(this, `plugin-detail:${this.kind}:${this.name}`, cmds);
  }

  async _toggle() {
    const action = this._info?.enabled !== false ? "disable" : "enable";
    const mutation = action === "enable"
      ? `mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }`
      : `mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }`;
    const { data } = await gqlFull(this.apiBase, mutation, { k: this.kind, n: this.name });
    const result = action === "enable" ? data?.enablePlugin : data?.disablePlugin;
    this._message = {
      type: result?.ok ? "success" : "error",
      text: result?.message || `${action} failed`,
    };
    await this._fetchInfo();
    this.dispatchEvent(new CustomEvent("plugin-state-changed", { bubbles: true, composed: true }));
  }

  async _sync() {
    this._syncing = true;
    this._message = null;
    try {
      const resp = await fetch(`${this.apiBase}/sync/${this.name}`, { method: "POST" });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        this._message = { type: "error", text: data.detail || `Sync failed (${resp.status})` };
        this._syncing = false;
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let lastEvent = "";
      let lastData = "";
      let hadError = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (line.startsWith("event: ")) lastEvent = line.slice(7).trim();
          if (line.startsWith("data: ")) lastData = line.slice(6);
        }
        if (lastEvent === "error") hadError = true;
      }
      let msg = "Sync complete";
      try { msg = JSON.parse(lastData).message || msg; } catch { /* use default */ }
      this._message = { type: hadError ? "error" : "success", text: msg };
      if (!hadError) await this._fetchInfo();
    } catch (e) {
      this._message = { type: "error", text: `Sync failed: ${e.message}` };
    }
    this._syncing = false;
  }

  async _runTransforms() {
    this._transforming = true;
    this._message = null;
    try {
      const { data } = await gqlFull(this.apiBase, `mutation($s: String!) { runSchemaTransforms(schema: $s) }`, { s: this.name });
      const tResult = data?.runSchemaTransforms;
      if (tResult?.count != null) {
        this._message = { type: "success", text: `Ran ${tResult.count} transform(s)` };
        await this._fetchInfo();
      } else {
        this._message = { type: "error", text: "Transform failed" };
      }
    } catch (e) {
      this._message = { type: "error", text: `Transform failed: ${e.message}` };
    }
    this._transforming = false;
  }

  async _flush() {
    this._message = null;
    try {
      const { data } = await gqlFull(this.apiBase, `mutation($s: String!) { flushSchema(schemaPlugin: $s) }`, { s: this.name });
      const fResult = data?.flushSchema;
      if (fResult?.rows_deleted != null) {
        this._message = { type: "success", text: `Flushed ${fResult.rows_deleted} rows` };
        await this._fetchInfo();
      } else {
        this._message = { type: "error", text: "Flush failed" };
      }
    } catch (e) {
      this._message = { type: "error", text: `Flush failed: ${e.message}` };
    }
  }

  async _remove() {
    const { data } = await gqlFull(this.apiBase, `mutation($k: String!, $n: String!) { removePlugin(kind: $k, name: $n) { ok message } }`, { k: this.kind, n: this.name });
    if (data?.removePlugin?.ok) {
      window.history.pushState({}, "", `/settings/${this.kind}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    } else {
      this._message = { type: "error", text: data?.removePlugin?.message || "Remove failed" };
    }
  }

  _switchTab(tab) {
    this.activeTab = tab;
    const base = `/settings/${this.kind}/${this.name}`;
    const path = tab === "details" ? base : `${base}/${tab}`;
    window.history.pushState({}, "", path);
  }

  async _fetchPreview(tableName) {
    this._selectedTable = tableName;
    if (!tableName) { this._previewRows = null; return; }
    this._previewLoading = true;
    const dbSchema = this.kind === "schema" ? "metrics" : this.name;
    this._previewRows = await arrowQuery(this.apiBase, `SELECT * FROM "${dbSchema}"."${tableName}" ORDER BY 1 DESC LIMIT 100`);
    this._previewLoading = false;
  }

  _renderData() {
    const tables = this._tables || [];
    if (tables.length === 0) return html`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;
    if (!this._selectedTable) {
      const primary = this._info?.primary_table;
      const target = primary && tables.some((t) => t.name === primary) ? primary : tables[0]?.name;
      if (target) this._fetchPreview(target);
    }
    return html`
      <div class="data-toolbar">
        <select @change=${(e) => this._fetchPreview(e.target.value)}>
          <option value="">Select a table</option>
          ${tables.map((t) => html`<option value=${t.name} ?selected=${this._selectedTable === t.name}>${t.name}${t.rows ? ` (${t.rows})` : ""}</option>`)}
        </select>
        ${this._previewLoading ? html`<span style="color:var(--shenas-text-muted,#888)">Loading...</span>` : ""}
      </div>
      ${this._previewRows && this._previewRows.length > 0 ? html`
        <table class="data-table">
          <thead><tr>${Object.keys(this._previewRows[0]).map((col) => html`<th>${col}</th>`)}</tr></thead>
          <tbody>${this._previewRows.map((row) => html`
            <tr>${Object.values(row).map((val) => html`<td title="${val ?? ""}">${val ?? ""}</td>`)}</tr>
          `)}</tbody>
        </table>
      ` : this._selectedTable && !this._previewLoading ? html`<p style="color:var(--shenas-text-muted,#888)">Table is empty.</p>` : ""}
    `;
  }

  render() {
    return html`
      <shenas-page ?loading=${this._loading} ?empty=${!this._info} empty-text="Plugin not found."
        display-name="${this._info?.display_name || this._info?.name || this.name}">
        ${this._info ? this._renderContent() : ""}
      </shenas-page>
    `;
  }

  _renderContent() {
    const info = this._info;
    const enabled = info.enabled !== false;

    const basePath = `/settings/${this.kind}/${this.name}`;

    return html`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <div class="title-row">
        <h2>${info.display_name || info.name} <span class="kind-badge">${info.kind}</span>${info.version ? html` <span class="version">${info.version}</span>` : ""}</h2>
        <div class="title-actions">
          ${this.kind === "pipe" && enabled
            ? html`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing ? "Syncing..." : "Sync"}</button>`
            : ""}
          ${this.kind === "schema"
            ? html`<button @click=${this._runTransforms} ?disabled=${this._transforming}>${this._transforming ? "Transforming..." : "Transform"}</button>`
            : ""}
          ${this.kind === "schema"
            ? html`<button class="danger" @click=${this._flush}>Flush</button>`
            : ""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${renderMessage(this._message)}

      <div class="tabs">
        <a class="tab" href="${basePath}" aria-selected=${this.activeTab === "details"}
          @click=${(e) => { e.preventDefault(); this._switchTab("details"); }}>Details</a>
        ${this._info?.has_config ? html`
          <a class="tab" href="${basePath}/config" aria-selected=${this.activeTab === "config"}
            @click=${(e) => { e.preventDefault(); this._switchTab("config"); }}>Config</a>
        ` : ""}
        ${this.kind === "pipe" ? html`
          <a class="tab" href="${basePath}/auth" aria-selected=${this.activeTab === "auth"}
            @click=${(e) => { e.preventDefault(); this._switchTab("auth"); }}>Auth</a>
        ` : ""}
        <a class="tab" href="${basePath}/data" aria-selected=${this.activeTab === "data"}
          @click=${(e) => { e.preventDefault(); this._switchTab("data"); }}>Data</a>
        <a class="tab" href="${basePath}/logs" aria-selected=${this.activeTab === "logs"}
          @click=${(e) => { e.preventDefault(); this._switchTab("logs"); }}>Logs</a>
      </div>

      ${this.activeTab === "config"
        ? html`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`
        : this.activeTab === "auth"
          ? html`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`
          : this.activeTab === "data"
            ? this._renderData()
            : this.activeTab === "logs"
              ? html`<shenas-logs api-base="${this.apiBase}" pipe="${this.name}"></shenas-logs>`
              : this._renderDetails(info, enabled)}
    `;
  }

  _renderDetails(info, enabled) {
    return html`
      ${info.description
        ? html`<div class="description">${info.description}</div>`
        : ""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-toggle ?enabled=${enabled} toggleable @toggle=${this._toggle}></status-toggle>
          </span>
        </div>
        ${this._stateRow("Last synced", info.synced_at)}
        ${this._stateRow("Added", info.added_at)}
        ${this._stateRow("Updated", info.updated_at)}
        ${this._stateRow("Status changed", info.status_changed_at)}
      </div>

      ${this.kind === "pipe" || this.kind === "schema"
        ? html`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[
              { key: "name", label: "Table", class: "mono" },
              { key: "rows", label: "Rows", class: "muted" },
              { label: "Range", class: "muted", render: (t) => t.earliest ? `${t.earliest} - ${t.latest}` : "" },
            ]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`
        : ""}

      ${this.kind === "pipe"
        ? html`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`
        : ""}

      ${this.kind === "schema" && this._schemaTransforms.length > 0
        ? html`
          <h4 class="section-title">Transforms</h4>
          <shenas-data-list
            .columns=${[
              { key: "id", label: "ID", class: "muted" },
              { label: "Source", class: "mono", render: (t) => `${t.sourceDuckdbSchema}.${t.sourceDuckdbTable}` },
              { label: "Target", class: "mono", render: (t) => `${t.targetDuckdbSchema}.${t.targetDuckdbTable}` },
              { label: "Description", render: (t) => t.description || "" },
              { label: "Status", render: (t) => html`<status-toggle ?enabled=${t.enabled}></status-toggle>` },
            ]}
            .rows=${this._schemaTransforms}
            .rowClass=${(t) => t.enabled ? "" : "disabled-row"}
            empty-text="No transforms"
          ></shenas-data-list>`
        : ""}

    `;
  }

  _stateRow(label, value) {
    if (!value) return "";
    return html`
      <div class="state-row">
        <span class="state-label">${label}</span>
        <span class="state-value">${value.slice(0, 19)}</span>
      </div>
    `;
  }
}

customElements.define("shenas-plugin-detail", PluginDetail);
