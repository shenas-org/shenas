import { LitElement, html, css } from "lit";
import {
  ApolloMutationController,
  getClient,
  gqlTag,
  registerCommands,
  renderMessage,
  buttonStyles,
  linkStyles,
  messageStyles,
  tabStyles,
} from "shenas-frontends";
import { GET_THEME, GET_SUGGESTED_DATASETS } from "./graphql/queries.ts";
import {
  ENABLE_PLUGIN,
  DISABLE_PLUGIN,
  RUN_SCHEMA_TRANSFORMS,
  FLUSH_SCHEMA,
  SUGGEST_DATASETS,
  ACCEPT_DATASET_SUGGESTION,
  DISMISS_DATASET_SUGGESTION,
} from "./graphql/mutations.ts";

interface PluginInfo {
  name: string;
  display_name?: string;
  kind: string;
  version?: string;
  description?: string;
  enabled?: boolean;
  synced_at?: string;
  added_at?: string;
  updated_at?: string;
  status_changed_at?: string;
  has_config?: boolean;
  has_auth?: boolean;
  has_data?: boolean;
  is_authenticated?: boolean | null;
  primary_table?: string;
}

interface TableInfo {
  name: string;
  rows?: number;
  cols?: number;
  earliest?: string;
  latest?: string;
}

interface SuggestedDataset {
  name: string;
  title?: string;
  grain?: string;
  tableName?: string;
}

interface SchemaTransform {
  id: number;
  source: { id: string; schemaName: string; tableName: string };
  target: { id: string; schemaName: string; tableName: string };
  sourcePlugin: string;
  description?: string;
  enabled: boolean;
}

interface DbStatus {
  schemas: Array<{ name: string; tables: TableInfo[] }>;
  [key: string]: unknown;
}

interface Message {
  type: string;
  text: string;
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
    _suggestions: { state: true },
    _suggesting: { state: true },
    _dataTable: { state: true },
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
        font-size: 1rem;
        margin-right: 0.4rem;
        text-decoration: none;
        vertical-align: middle;
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
      .data-table th,
      .data-table td {
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
      shenas-data-table {
        margin: 0 -1rem;
        width: calc(100% + 2rem);
      }
      .tab-select {
        border: none;
        background: transparent;
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        padding: 0.4rem 0.2rem;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        align-self: stretch;
        -webkit-appearance: none;
        appearance: none;
      }
      .tab-select:focus {
        outline: none;
      }
      .suggestion-card {
        border: 1px solid var(--shenas-border, #ccc);
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
      }
      .suggestion-card h5 {
        margin: 0 0 0.3rem;
        font-size: 0.9rem;
      }
      .suggestion-meta {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        margin-bottom: 0.5rem;
      }
      .suggestion-actions {
        display: flex;
        gap: 0.4rem;
      }
      .suggestion-actions button {
        padding: 0.25rem 0.6rem;
        font-size: 0.8rem;
      }
    `,
  ];

  declare apiBase: string;
  declare kind: string;
  declare name: string;
  declare activeTab: string;
  declare dbStatus: DbStatus | null;
  declare schemaPlugins: Record<string, string[]>;
  declare initialInfo: PluginInfo | null;
  declare _info: PluginInfo | null;
  declare _loading: boolean;
  declare _showLoading: boolean;
  declare _message: Message | null;
  declare _tables: TableInfo[];
  declare _syncing: boolean;
  declare _transforming: boolean;
  declare _schemaTransforms: SchemaTransform[];
  declare _suggestions: SuggestedDataset[];
  declare _suggesting: boolean;
  declare _dataTable: string;
  private _loadingTimer: ReturnType<typeof setTimeout> | null = null;

  private _client = getClient();
  private _enablePlugin = new ApolloMutationController(this, ENABLE_PLUGIN, { client: this._client });
  private _disablePlugin = new ApolloMutationController(this, DISABLE_PLUGIN, { client: this._client });
  private _runSchemaTransforms = new ApolloMutationController(this, RUN_SCHEMA_TRANSFORMS, { client: this._client });
  private _flushSchema = new ApolloMutationController(this, FLUSH_SCHEMA, { client: this._client });
  private _suggestDatasetsMutation = new ApolloMutationController(this, SUGGEST_DATASETS, { client: this._client });
  private _acceptDatasetSuggestion = new ApolloMutationController(this, ACCEPT_DATASET_SUGGESTION, {
    client: this._client,
  });
  private _dismissDatasetSuggestion = new ApolloMutationController(this, DISMISS_DATASET_SUGGESTION, {
    client: this._client,
  });

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this.activeTab = "details";
    this.dbStatus = null;
    this.schemaPlugins = {};
    this.initialInfo = null;
    this._info = null;
    this._loading = true;
    this._showLoading = false;
    this._message = null;
    this._tables = [];
    this._syncing = false;
    this._transforming = false;
    this._schemaTransforms = [];
    this._suggestions = [];
    this._suggesting = false;
    this._dataTable = "";
  }

  willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("kind") || changed.has("name")) {
      // Check for OAuth callback result in URL
      const params = new URLSearchParams(window.location.search);
      const authResult = params.get("auth");

      if (!authResult && this.initialInfo && !this._info) {
        this._info = this.initialInfo;
        this._loading = false;
        this._showLoading = false;
      }
      this._fetchInfo();

      if (authResult) {
        if (authResult === "success") {
          this._message = { type: "success", text: "Authentication successful" };
          this.activeTab = "auth";
        } else {
          this._message = { type: "error", text: params.get("message") || "Authentication failed" };
          this.activeTab = "auth";
        }
        // Clean up the URL
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
    if (changed.has("_loading")) {
      if (this._loadingTimer) clearTimeout(this._loadingTimer);
      if (this._loading) {
        this._loadingTimer = setTimeout(() => {
          this._showLoading = true;
        }, 200);
      } else {
        this._showLoading = false;
      }
    }
  }

  async _fetchInfo(): Promise<void> {
    if (!this.kind || !this.name) return;
    this._loading = true;
    this._message = null;
    const needsSchema = this.kind === "dataset";
    const fields = [
      `pluginInfo(kind: $kind, name: $name)`,
      needsSchema
        ? `transforms { id source { id schemaName tableName } target { id schemaName tableName } sourcePlugin description enabled }`
        : "",
    ]
      .filter(Boolean)
      .join(" ");
    const { data } = await this._client.query({
      query: gqlTag([`query($kind: String!, $name: String!) { ${fields} }`] as unknown as TemplateStringsArray),
      variables: { kind: this.kind, name: this.name },
      fetchPolicy: "network-only",
    });
    this._info = data?.pluginInfo as PluginInfo | null;
    if (!this.dbStatus) {
      try {
        const { data: dbData } = await this._client.query({
          query: gqlTag`{ dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } } }`,
          fetchPolicy: "network-only",
        });
        this.dbStatus = (dbData?.dbStatus as DbStatus | null) ?? null;
      } catch {
        /* ignore */
      }
    }
    const db = this.dbStatus;
    const ownership = this.schemaPlugins;
    const allTransforms = data?.transforms as SchemaTransform[] | undefined;
    const ownedTables = ownership ? ownership[this.name] || [] : [];
    if (db) {
      if (this.kind === "source") {
        const schema = (db.schemas || []).find((s) => s.name === this.name);
        this._tables = schema ? schema.tables.filter((t) => !t.name.startsWith("_dlt_")) : [];
      } else if (this.kind === "dataset") {
        const metricsSchema = (db.schemas || []).find((s) => s.name === "metrics");
        this._tables = metricsSchema ? metricsSchema.tables.filter((t) => ownedTables.includes(t.name)) : [];
      }
    }
    if (allTransforms) {
      this._schemaTransforms = allTransforms.filter((t) => ownedTables.includes(t.target.tableName));
    }
    this._loading = false;
    this._registerCommands();
  }

  _registerCommands(): void {
    if (!this._info) return;
    const label = this._info.display_name || this.name;
    const cmds = [
      {
        id: `remove:${this.kind}:${this.name}`,
        category: "Plugin",
        label: `Remove ${label}`,
        action: () => this._remove(),
      },
    ];
    if (this.kind === "dataset") {
      cmds.unshift(
        {
          id: `flush:${this.kind}:${this.name}`,
          category: "Plugin",
          label: `Flush ${label}`,
          action: () => this._flush(),
        },
        {
          id: `transform:${this.kind}:${this.name}`,
          category: "Plugin",
          label: `Transform ${label}`,
          action: () => this._runTransforms(),
        },
      );
    }
    registerCommands(this, `plugin-detail:${this.kind}:${this.name}`, cmds);
  }

  async _toggle(): Promise<void> {
    const action = this._info?.enabled !== false ? "disable" : "enable";
    const controller = action === "enable" ? this._enablePlugin : this._disablePlugin;
    const { data } = await controller.mutate({ variables: { k: this.kind, n: this.name } });
    const result = (action === "enable" ? data?.enablePlugin : data?.disablePlugin) as
      | Record<string, unknown>
      | undefined;
    this._message = {
      type: result?.ok ? "success" : "error",
      text: (result?.message as string) || `${action} failed`,
    };
    await this._fetchInfo();
    if (this.kind === "theme") {
      const { data: themeData } = await this._client.query({ query: GET_THEME, fetchPolicy: "network-only" });
      const themeCss = (themeData?.theme as Record<string, unknown>)?.css as string | undefined;
      let link = document.querySelector("link[data-shenas-theme]") as HTMLLinkElement | null;
      if (themeCss) {
        if (!link) {
          link = document.createElement("link");
          link.rel = "stylesheet";
          link.setAttribute("data-shenas-theme", "");
          document.head.appendChild(link);
        }
        link.href = themeCss;
      } else if (link) {
        link.remove();
      }
    }
    if (this.kind === "ui" && action === "enable") {
      window.location.replace(window.location.pathname + "?_switch=" + Date.now());
      return;
    }
    this.dispatchEvent(new CustomEvent("plugin-state-changed", { bubbles: true, composed: true }));
  }

  async _sync(): Promise<void> {
    this._syncing = true;
    this._message = null;
    const displayName = this._info?.display_name || this.name;
    const jobId = `sync-${this.name}-${Date.now()}`;
    this.dispatchEvent(
      new CustomEvent("job-start", {
        bubbles: true,
        composed: true,
        detail: { id: jobId, label: `Syncing ${displayName}` },
      }),
    );
    try {
      const resp = await fetch(`${this.apiBase}/sync/${this.name}`, { method: "POST" });
      if (!resp.ok) {
        const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
        const errMsg = (data.detail as string) || `Sync failed (${resp.status})`;
        this._message = { type: "error", text: errMsg };
        this.dispatchEvent(
          new CustomEvent("job-finish", {
            bubbles: true,
            composed: true,
            detail: { id: jobId, ok: false, message: errMsg },
          }),
        );
        this._syncing = false;
        return;
      }
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let lastEvent = "";
      let lastData = "";
      let lastLogged = "";
      let hadError = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (line.startsWith("event: ")) lastEvent = line.slice(7).trim();
          if (line.startsWith("data: ")) {
            lastData = line.slice(6);
            try {
              const d = JSON.parse(lastData) as Record<string, unknown>;
              // Use the message; do NOT fall back to source -- that just echoes
              // the source name and produces noise. Skip empty + duplicate-of-last.
              const msg = d.message;
              const logText = typeof msg === "string" ? msg : "";
              if (logText && logText !== lastLogged) {
                lastLogged = logText;
                this.dispatchEvent(
                  new CustomEvent("job-log", {
                    bubbles: true,
                    composed: true,
                    detail: { id: jobId, text: logText },
                  }),
                );
              }
            } catch {
              /* skip */
            }
          }
        }
        if (lastEvent === "error") hadError = true;
      }
      let msg = "Sync complete";
      try {
        msg = ((JSON.parse(lastData) as Record<string, unknown>).message as string) || msg;
      } catch {
        /* use default */
      }
      this._message = { type: hadError ? "error" : "success", text: msg };
      this.dispatchEvent(
        new CustomEvent("job-finish", {
          bubbles: true,
          composed: true,
          detail: { id: jobId, ok: !hadError, message: msg },
        }),
      );
      if (!hadError) await this._fetchInfo();
    } catch (e) {
      const err = e as Error;
      this._message = { type: "error", text: `Sync failed: ${err.message}` };
      this.dispatchEvent(
        new CustomEvent("job-finish", {
          bubbles: true,
          composed: true,
          detail: { id: jobId, ok: false, message: err.message },
        }),
      );
    }
    this._syncing = false;
  }

  async _runTransforms(): Promise<void> {
    this._transforming = true;
    this._message = null;
    try {
      const { data } = await this._runSchemaTransforms.mutate({ variables: { schema: this.name } });
      const tResult = data?.runSchemaTransforms as Record<string, unknown> | undefined;
      if (tResult?.count != null) {
        this._message = { type: "success", text: `Ran ${tResult.count} transform(s)` };
        await this._fetchInfo();
      } else {
        this._message = { type: "error", text: "Transform failed" };
      }
    } catch (e) {
      this._message = { type: "error", text: `Transform failed: ${(e as Error).message}` };
    }
    this._transforming = false;
  }

  async _flush(): Promise<void> {
    this._message = null;
    try {
      const { data } = await this._flushSchema.mutate({ variables: { s: this.name } });
      const fResult = data?.flushSchema as Record<string, unknown> | undefined;
      if (fResult?.rows_deleted != null) {
        this._message = { type: "success", text: `Flushed ${fResult.rows_deleted} rows` };
        await this._fetchInfo();
      } else {
        this._message = { type: "error", text: "Flush failed" };
      }
    } catch (e) {
      this._message = { type: "error", text: `Flush failed: ${(e as Error).message}` };
    }
  }

  async _remove(): Promise<void> {
    const displayName =
      this._info?.display_name || this.name.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const jobId = `remove-${this.kind}-${this.name}-${Date.now()}`;

    this.dispatchEvent(
      new CustomEvent("job-start", {
        bubbles: true,
        composed: true,
        detail: { id: jobId, label: `Removing ${displayName}` },
      }),
    );

    try {
      const resp = await fetch(`${this.apiBase}/plugins/${this.kind}/${this.name}/remove-stream`, { method: "POST" });
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let ok = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop()!;
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6)) as Record<string, unknown>;
            if (evt.event === "log") {
              this.dispatchEvent(
                new CustomEvent("job-log", { bubbles: true, composed: true, detail: { id: jobId, text: evt.text } }),
              );
            } else if (evt.event === "done") {
              ok = evt.ok as boolean;
              this.dispatchEvent(
                new CustomEvent("job-finish", {
                  bubbles: true,
                  composed: true,
                  detail: { id: jobId, ok: evt.ok, message: evt.message },
                }),
              );
            }
          } catch {
            /* skip */
          }
        }
      }

      if (ok) {
        this.dispatchEvent(new CustomEvent("plugins-changed", { bubbles: true, composed: true, detail: null }));
        window.history.pushState({}, "", `/settings/${this.kind}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
      } else {
        this._message = { type: "error", text: "Remove failed" };
      }
    } catch (err) {
      const error = err as Error;
      this.dispatchEvent(
        new CustomEvent("job-finish", {
          bubbles: true,
          composed: true,
          detail: { id: jobId, ok: false, message: error.message },
        }),
      );
      this._message = { type: "error", text: error.message };
    }
  }

  _switchTab(tab: string): void {
    this.activeTab = tab;
    const base = `/settings/${this.kind}/${this.name}`;
    const path = tab === "details" ? base : `${base}/${tab}`;
    window.history.pushState({}, "", path);
    if (tab === "transforms") this._fetchSuggestions();
  }

  _renderData() {
    const tables = (this._tables || []).filter((t) => !t.name.startsWith("_dlt_"));
    if (tables.length === 0) return html`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;
    const schema = this.kind === "dataset" ? "metrics" : this._info?.name || this.name;
    const table = this._dataTable || this._info?.primary_table || tables[0]?.name || "";
    if (!this._dataTable && table) {
      requestAnimationFrame(() => {
        this._dataTable = table;
      });
    }
    this._ensureDataTableScript();
    return html`<shenas-data-table
      api-base="${this.apiBase}"
      schema="${schema}"
      table="${table}"
      page-size="100"
      style="height:calc(100vh - 180px);min-height:300px"
    ></shenas-data-table>`;
  }

  _ensureDataTableScript(): void {
    if (customElements.get("shenas-data-table")) return;
    const src = "/dashboards/data-table/data-table.js";
    if (document.querySelector(`script[src="${src}"]`)) return;
    const script = document.createElement("script");
    script.type = "module";
    script.src = src;
    document.head.appendChild(script);
  }

  render() {
    return html`
      <shenas-page
        ?loading=${this._showLoading}
        ?empty=${!this._loading && !this._info}
        empty-text="Plugin not found."
        display-name="${this._info?.display_name || this._info?.name || this.name}"
      >
        ${this._info ? this._renderContent() : ""}
      </shenas-page>
    `;
  }

  _renderContent() {
    const info = this._info!;
    const enabled = info.enabled !== false;

    const basePath = `/settings/${this.kind}/${this.name}`;

    return html`
      <div class="title-row">
        <h2>
          <a
            class="back"
            href="/settings/${this.kind}"
            @click=${(e: MouseEvent) => {
              e.preventDefault();
              window.history.pushState({}, "", `/settings/${this.kind}`);
              window.dispatchEvent(new PopStateEvent("popstate"));
            }}
            >&larr;</a
          >
          ${(info as Record<string, unknown>).icon_url
            ? html`<img
                src="${(info as Record<string, unknown>).icon_url}"
                alt=""
                style="width:1.6rem;height:1.6rem;vertical-align:middle;margin-right:0.4rem"
                @error=${(e: Event) => {
                  const img = e.target as HTMLImageElement;
                  const span = document.createElement("span");
                  span.textContent = "\u{1F4E6}";
                  span.style.cssText = "font-size:1.4rem;vertical-align:middle;margin-right:0.4rem";
                  img.replaceWith(span);
                }}
              />`
            : html`<span style="font-size:1.4rem;vertical-align:middle;margin-right:0.4rem"
                >&#x1F4E6;</span
              >`}${info.display_name || info.name} <span class="kind-badge">${info.kind}</span>${info.version
            ? html` <span class="version">${info.version}</span>`
            : ""}
        </h2>
        <div class="title-actions">
          ${this.kind === "source" && enabled
            ? html`<button
                @click=${this._sync}
                ?disabled=${this._syncing || (info.has_auth && info.is_authenticated === false)}
                title=${info.has_auth && info.is_authenticated === false ? "Authenticate first" : ""}
              >
                ${this._syncing ? "Syncing..." : "Sync"}
              </button>`
            : ""}
          ${this.kind === "dataset"
            ? html`<button @click=${this._runTransforms} ?disabled=${this._transforming}>
                ${this._transforming ? "Transforming..." : "Transform"}
              </button>`
            : ""}
          ${this.kind === "dataset" ? html`<button class="danger" @click=${this._flush}>Flush</button>` : ""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${renderMessage(this._message)}

      <div class="tabs">
        <a
          class="tab"
          href="${basePath}"
          aria-selected=${this.activeTab === "details"}
          @click=${(e: MouseEvent) => {
            e.preventDefault();
            this._switchTab("details");
          }}
          >Details</a
        >
        ${this._info?.has_config
          ? html`
              <a
                class="tab"
                href="${basePath}/config"
                aria-selected=${this.activeTab === "config"}
                @click=${(e: MouseEvent) => {
                  e.preventDefault();
                  this._switchTab("config");
                }}
                >Config</a
              >
            `
          : ""}
        ${this._info?.has_auth
          ? html`
              <a
                class="tab"
                href="${basePath}/auth"
                aria-selected=${this.activeTab === "auth"}
                @click=${(e: MouseEvent) => {
                  e.preventDefault();
                  this._switchTab("auth");
                }}
                >Auth</a
              >
            `
          : ""}
        ${this.kind === "source"
          ? html`
              <a
                class="tab"
                href="${basePath}/transforms"
                aria-selected=${this.activeTab === "transforms"}
                @click=${(e: MouseEvent) => {
                  e.preventDefault();
                  this._switchTab("transforms");
                }}
                >Transforms</a
              >
            `
          : ""}
        ${this._info?.has_data !== false
          ? html`
              <a
                class="tab"
                href="${basePath}/data"
                aria-selected=${this.activeTab === "data"}
                @click=${(e: MouseEvent) => {
                  e.preventDefault();
                  this._switchTab("data");
                }}
                >Data</a
              >
              ${this.activeTab === "data" && this._tables.length > 0
                ? html`<select
                    class="tab-select"
                    @change=${(e: Event) => {
                      this._dataTable = (e.target as HTMLSelectElement).value;
                    }}
                  >
                    ${this._tables
                      .filter((t) => !t.name.startsWith("_dlt_"))
                      .map(
                        (t) =>
                          html`<option value=${t.name} ?selected=${this._dataTable === t.name}>
                            ${t.name}${t.rows ? ` (${t.rows})` : ""}
                          </option>`,
                      )}
                  </select>`
                : ""}
            `
          : ""}
        <a
          class="tab"
          href="${basePath}/logs"
          aria-selected=${this.activeTab === "logs"}
          @click=${(e: MouseEvent) => {
            e.preventDefault();
            this._switchTab("logs");
          }}
          >Logs</a
        >
      </div>

      ${this.activeTab === "config"
        ? html`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`
        : this.activeTab === "auth"
          ? html`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`
          : this.activeTab === "transforms"
            ? this._renderTransforms()
            : this.activeTab === "data"
              ? this._renderData()
              : this.activeTab === "logs"
                ? html`<shenas-logs api-base="${this.apiBase}" pipe="${this.name}"></shenas-logs>`
                : this._renderDetails(info, enabled)}
    `;
  }

  _renderDetails(info: PluginInfo, enabled: boolean) {
    return html`
      ${info.description ? html`<div class="description">${info.description}</div>` : ""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-toggle ?enabled=${enabled} toggleable @toggle=${this._toggle}></status-toggle>
          </span>
        </div>
        ${this._stateRow("Last synced", info.synced_at)} ${this._stateRow("Added", info.added_at)}
        ${this._stateRow("Updated", info.updated_at)} ${this._stateRow("Status changed", info.status_changed_at)}
      </div>

      ${this.kind === "source" || this.kind === "dataset"
        ? html` <h4 class="section-title">Resources</h4>
            <shenas-data-list
              .columns=${[
                { key: "name", label: "Table", class: "mono" },
                { key: "rows", label: "Rows", class: "muted" },
                {
                  label: "Range",
                  class: "muted",
                  render: (t: TableInfo) => (t.earliest ? `${t.earliest} - ${t.latest}` : ""),
                },
              ]}
              .rows=${this._tables}
              empty-text="No tables synced yet"
            ></shenas-data-list>`
        : ""}
      ${this.kind === "dataset" && this._schemaTransforms.length > 0
        ? html` <h4 class="section-title">Transforms</h4>
            <shenas-data-list
              .columns=${[
                { key: "id", label: "ID", class: "muted" },
                {
                  label: "Source",
                  class: "mono",
                  render: (t: SchemaTransform) => `${t.source.schemaName}.${t.source.tableName}`,
                },
                {
                  label: "Target",
                  class: "mono",
                  render: (t: SchemaTransform) => `${t.target.schemaName}.${t.target.tableName}`,
                },
                { label: "Description", render: (t: SchemaTransform) => t.description || "" },
                {
                  label: "Status",
                  render: (t: SchemaTransform) => html`<status-toggle ?enabled=${t.enabled}></status-toggle>`,
                },
              ]}
              .rows=${this._schemaTransforms}
              .rowClass=${(t: SchemaTransform) => (t.enabled ? "" : "disabled-row")}
              empty-text="No transforms"
            ></shenas-data-list>`
        : ""}
    `;
  }

  _renderTransforms() {
    return html`
      <shenas-transforms
        api-base="${this.apiBase}"
        source="${this.name}"
        ?show-suggest=${true}
        ?suggesting=${this._suggesting}
        @suggest=${this._suggestDatasets}
      ></shenas-transforms>

      ${this._suggestions.length > 0
        ? html`
            <h4 class="section-title">Suggested Metrics</h4>
            ${this._suggestions.map(
              (s) => html`
                <div class="suggestion-card">
                  <h5>${s.title || s.name}</h5>
                  <div class="suggestion-meta">
                    ${s.tableName ? html`Table: <code>${s.tableName}</code>` : ""}
                    ${s.grain ? html` &middot; Grain: ${s.grain}` : ""}
                  </div>
                  <div class="suggestion-actions">
                    <button @click=${() => this._acceptSuggestion(s.name)}>Accept</button>
                    <button class="danger" @click=${() => this._dismissSuggestion(s.name)}>Dismiss</button>
                  </div>
                </div>
              `,
            )}
          `
        : ""}
    `;
  }

  async _fetchSuggestions(): Promise<void> {
    const { data } = await this._client.query({ query: GET_SUGGESTED_DATASETS, fetchPolicy: "network-only" });
    this._suggestions = (data?.suggestedDatasets as SuggestedDataset[]) || [];
  }

  async _suggestDatasets(): Promise<void> {
    this._suggesting = true;
    this._message = null;
    try {
      const { data } = await this._suggestDatasetsMutation.mutate({ variables: { source: this.name } });
      if (!data) {
        this._message = { type: "error", text: "Suggestion failed" };
      } else {
        const result = data.suggestDatasets as Record<string, unknown> | undefined;
        if (result?.ok === false) {
          this._message = { type: "error", text: (result.error as string) || "Suggestion failed" };
        } else {
          const suggestions = (result?.suggestions as SuggestedDataset[]) || [];
          this._message = { type: "success", text: `Generated ${suggestions.length} suggestion(s)` };
          await this._fetchSuggestions();
        }
      }
    } catch (e) {
      this._message = { type: "error", text: `Suggestion failed: ${(e as Error).message}` };
    }
    this._suggesting = false;
  }

  async _acceptSuggestion(name: string): Promise<void> {
    const { data } = await this._acceptDatasetSuggestion.mutate({ variables: { name } });
    const result = data?.acceptDatasetSuggestion as Record<string, unknown> | undefined;
    if (result?.ok) {
      this._suggestions = this._suggestions.filter((s) => s.name !== name);
      this._message = { type: "success", text: (result.message as string) || "Suggestion accepted" };
    } else {
      this._message = { type: "error", text: (result?.message as string) || "Accept failed" };
    }
  }

  async _dismissSuggestion(name: string): Promise<void> {
    const { data } = await this._dismissDatasetSuggestion.mutate({ variables: { name } });
    const result = data?.dismissDatasetSuggestion as Record<string, unknown> | undefined;
    if (result?.ok) {
      this._suggestions = this._suggestions.filter((s) => s.name !== name);
    } else {
      this._message = { type: "error", text: (result?.message as string) || "Dismiss failed" };
    }
  }

  _stateRow(label: string, value?: string) {
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
