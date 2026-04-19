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
import "shenas-components";
import { GET_THEME, GET_SUGGESTED_DATASETS, GET_SOURCE_ENTITIES } from "./graphql/queries.ts";
import {
  ENABLE_PLUGIN,
  DISABLE_PLUGIN,
  RUN_DATASET_TRANSFORMS,
  FLUSH_SCHEMA,
  SUGGEST_DATASETS,
  ACCEPT_DATASET_SUGGESTION,
  DISMISS_DATASET_SUGGESTION,
  SET_ENTITY_STATUS,
  UPDATE_ENTITY,
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
  has_entities?: boolean;
  is_authenticated?: boolean | null;
  primary_table?: string;
  icon_url?: string;
  tables?: string[];
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
  transformType: string;
  transformTypeDisplayName: string;
  source: { id: string; schemaName: string; tableName: string; displayName: string; plugin?: { displayName: string } };
  target: { id: string; schemaName: string; tableName: string; displayName: string };
  sourcePlugin: string;
  description?: string;
  enabled: boolean;
}

interface SourceEntity {
  uuid: string;
  type: string;
  name: string;
  description: string;
  status: string;
}

interface EntityTypeOption {
  name: string;
  displayName: string;
  isAbstract: boolean;
  parent: string | null;
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
    initialInfo: { type: Object },
    datasetTables: { type: Array },
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
    _dataRefreshKey: { state: true },
    _entities: { state: true },
    _entityTypes: { state: true },
    _entitiesLoading: { state: true },
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
      .add-entity-btn {
        background: transparent;
        border: 1px solid var(--shenas-border, #ddd);
        border-radius: 3px;
        color: var(--shenas-text-muted, #888);
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
        padding: 0.15rem 0.4rem;
      }
      .add-entity-btn:hover {
        background: var(--shenas-bg-secondary, #f0f0f0);
        color: var(--shenas-text, #333);
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
  declare initialInfo: PluginInfo | null;
  declare datasetTables: string[];
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
  declare _dataRefreshKey: number;
  declare _entities: SourceEntity[];
  declare _entityTypes: EntityTypeOption[];
  declare _entitiesLoading: boolean;
  private _loadingTimer: ReturnType<typeof setTimeout> | null = null;

  private _client = getClient();
  private _setEntityStatusMutation = new ApolloMutationController(this, SET_ENTITY_STATUS, { client: this._client });
  private _updateEntityMutation = new ApolloMutationController(this, UPDATE_ENTITY, { client: this._client });
  private _enablePlugin = new ApolloMutationController(this, ENABLE_PLUGIN, { client: this._client });
  private _disablePlugin = new ApolloMutationController(this, DISABLE_PLUGIN, { client: this._client });
  private _runDatasetTransforms = new ApolloMutationController(this, RUN_DATASET_TRANSFORMS, { client: this._client });
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
    this._dataRefreshKey = 0;
    this._entities = [];
    this._entityTypes = [];
    this._entitiesLoading = false;
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
      if (this.activeTab === "entities") {
        this._fetchEntities();
      }

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
        ? `transforms { id transformType transformTypeDisplayName source { id schemaName tableName displayName plugin { displayName } } target { id schemaName tableName displayName } sourcePlugin description enabled }`
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
    const allTransforms = data?.transforms as SchemaTransform[] | undefined;
    const ownedTables = this._info?.tables || [];
    // Build _tables from plugin table_metadata (includes live stats).
    const tableMeta =
      ((this._info as unknown as Record<string, unknown>)?.table_metadata as {
        table: string;
        rows?: number;
        earliest?: string;
        latest?: string;
      }[]) || [];
    this._tables = tableMeta.map((entry) => ({
      name: entry.table,
      rows: entry.rows || 0,
      earliest: entry.earliest || undefined,
      latest: entry.latest || undefined,
    }));
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
      if (!hadError) {
        this._dataRefreshKey = this._dataRefreshKey + 1;
        await this._fetchInfo();
        if (this.activeTab === "entities") {
          this._fetchEntities();
        }
      }
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
      const { data } = await this._runDatasetTransforms.mutate({ variables: { dataset: this.name } });
      const tResult = data?.runDatasetTransforms as Record<string, unknown> | undefined;
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
    if (tab === "entities") this._fetchEntities();
    if (tab === "data" && this.kind === "dataset") this._fetchInfo();
  }

  async _fetchEntities(): Promise<void> {
    this._entitiesLoading = true;
    try {
      const result = await this._client.query({
        query: GET_SOURCE_ENTITIES,
        variables: { plugin: this.name },
        fetchPolicy: "network-only",
      });
      this._entities = (result.data?.sourceEntitiesForPlugin as SourceEntity[]) || [];
      this._entityTypes = (result.data?.entityTypes as EntityTypeOption[]) || [];
    } catch (e) {
      this._message = { type: "error", text: (e as Error).message };
    }
    this._entitiesLoading = false;
  }

  async _toggleEntityStatus(entity: SourceEntity): Promise<void> {
    const next = entity.status === "enabled" ? "disabled" : "enabled";
    this._entities = this._entities.map((e) => (e.uuid === entity.uuid ? { ...e, status: next } : e));
    try {
      await this._setEntityStatusMutation.mutate({ variables: { uuid: entity.uuid, status: next } });
    } catch (e) {
      this._entities = this._entities.map((e) => (e.uuid === entity.uuid ? { ...e, status: entity.status } : e));
      this._message = { type: "error", text: (e as Error).message };
    }
  }

  async _changeEntityType(entity: SourceEntity, newType: string): Promise<void> {
    this._entities = this._entities.map((existing) =>
      existing.uuid === entity.uuid ? { ...existing, type: newType } : existing,
    );
    try {
      await this._updateEntityMutation.mutate({ variables: { uuid: entity.uuid, input: { type: newType } } });
    } catch (error) {
      this._entities = this._entities.map((existing) =>
        existing.uuid === entity.uuid ? { ...existing, type: entity.type } : existing,
      );
      this._message = { type: "error", text: (error as Error).message };
    }
  }

  _renderEntities() {
    if (this._entitiesLoading && this._entities.length === 0) {
      return html`<p style="color:var(--shenas-text-muted,#888)">Loading entities...</p>`;
    }
    if (this._entities.length === 0) {
      return html`<p style="color:var(--shenas-text-muted,#888)">
        No entities yet. Sync this source to populate the list.
      </p>`;
    }
    return this._renderEntitySection();
  }

  _renderEntitySection() {
    const enabledCount = this._entities.filter((e) => e.status === "enabled").length;
    return html`
      <h3 style="margin:1.2rem 0 0.3rem;font-size:0.95rem">Entities</h3>
      <p style="color:var(--shenas-text-muted,#888);font-size:0.85rem;margin:0 0 0.8rem">
        ${enabledCount} of ${this._entities.length} enabled. Toggle to show or hide in the entity graph.
      </p>
      <shenas-data-list
        .columns=${[
          {
            key: "name",
            label: "Name",
            render: (row: Record<string, unknown>) => {
              const entity = row as unknown as SourceEntity;
              return entity.name || entity.uuid.slice(0, 8);
            },
          },
          {
            label: "Type",
            render: (row: Record<string, unknown>) => {
              const entity = row as unknown as SourceEntity;
              const concreteTypes = this._entityTypes.filter((entityType) => !entityType.isAbstract);
              return html`<select
                .value=${entity.type}
                @change=${(event: Event) => {
                  const newType = (event.target as HTMLSelectElement).value;
                  if (newType !== entity.type) this._changeEntityType(entity, newType);
                }}
                style="font-size:0.85rem;padding:2px 4px;border:1px solid var(--shenas-border-light,#ddd);border-radius:3px;background:transparent"
              >
                ${concreteTypes.map(
                  (entityType) =>
                    html`<option value=${entityType.name} ?selected=${entity.type === entityType.name}>
                      ${entityType.displayName}
                    </option>`,
                )}
              </select>`;
            },
          },
          {
            key: "status",
            label: "Enabled",
            render: (row: Record<string, unknown>) => {
              const entity = row as unknown as SourceEntity;
              return html`<input
                type="checkbox"
                title=${entity.status === "enabled" ? "Shown in entity graph" : "Hidden from entity graph"}
                .checked=${entity.status === "enabled"}
                @change=${() => this._toggleEntityStatus(entity)}
              />`;
            },
          },
        ]}
        .rows=${this._entities as unknown as Record<string, unknown>[]}
        empty-text="No entities"
      ></shenas-data-list>
    `;
  }

  _tableDisplayName(dbName: string): string {
    const declared = ((this._info as unknown as Record<string, unknown>)?.table_metadata || []) as {
      table: string;
      display_name: string;
    }[];
    for (const entry of declared) {
      if (entry.table === dbName) return entry.display_name || dbName;
    }
    return dbName;
  }

  _renderData() {
    const tables = (this._tables || []).filter((t) => !t.name.startsWith("_dlt_"));
    const defaultSchema = this.kind === "dataset" ? "datasets" : "sources";

    // Sources that write to a non-source schema (e.g. wikidata -> entities.countries)
    // can declare it on primary_table as "<schema>.<table>". Honor that even
    // when the plugin's own schema is empty -- otherwise the Data tab would
    // hide the entity rows the source actually owns.
    let primaryFallbackSchema: string | null = null;
    let primaryFallbackTable: string | null = null;
    if (this._info?.primary_table?.includes(".")) {
      const [s, t] = this._info.primary_table.split(".", 2);
      primaryFallbackSchema = s;
      primaryFallbackTable = t;
    }

    if (tables.length === 0 && !primaryFallbackTable) {
      const declared = (this._info as unknown as Record<string, unknown>)?.table_metadata as
        | {
            table: string;
            display_name: string;
            description: string;
            kind: string;
            columns: { name: string; db_type: string; description: string }[];
          }[]
        | undefined;
      if (declared && declared.length > 0) {
        return this._renderDeclaredSchema(declared);
      }
      return html`<p style="color:var(--shenas-text-muted,#888)">No tables synced yet.</p>`;
    }

    const schema = primaryFallbackSchema ?? defaultSchema;
    const tableNames = new Set(tables.map((t) => t.name));
    const urlTable = new URLSearchParams(window.location.search).get("table");
    const preferred = urlTable || this._dataTable || primaryFallbackTable || this._info?.primary_table || "";
    const table = (preferred && tableNames.has(preferred) ? preferred : tables[0]?.name) || "";
    if (!this._dataTable && table) {
      requestAnimationFrame(() => {
        this._dataTable = table;
      });
    }
    const tableMeta =
      ((this._info as unknown as Record<string, unknown>)?.table_metadata as Record<string, unknown>[]) || [];
    const matchingMeta = tableMeta.find((entry) => entry.table === table) || null;
    const viewParam = new URLSearchParams(window.location.search).get("view") || "table";
    return html`<shenas-data-table
      api-base="${this.apiBase}"
      schema="${schema}"
      table="${table}"
      data-view="${viewParam}"
      .tableMetadata=${matchingMeta}
      page-size="100"
      refresh-key="${this._dataRefreshKey}"
      @view-change=${(event: CustomEvent) => {
        const url = new URL(window.location.href);
        if (event.detail.view === "table") {
          url.searchParams.delete("view");
        } else {
          url.searchParams.set("view", event.detail.view);
        }
        window.history.pushState({}, "", url.toString());
      }}
      style="height:calc(100vh - 180px);min-height:300px"
    ></shenas-data-table>`;
  }

  _renderDeclaredSchema(
    declared: {
      table: string;
      display_name: string;
      description: string;
      kind: string;
      columns: { name: string; db_type: string; description: string }[];
    }[],
  ) {
    return html`
      <p style="color:var(--shenas-text-muted,#888);margin-bottom:1rem">Not yet synced. Declared tables:</p>
      ${declared.map(
        (t) => html`
          <details style="margin-bottom:0.8rem">
            <summary style="cursor:pointer;font-weight:600;font-size:0.9rem">
              ${t.display_name || t.table}
              ${t.kind
                ? html`<span
                    style="font-weight:400;color:var(--shenas-text-muted,#888);margin-left:0.5rem;font-size:0.8rem"
                    >${t.kind}</span
                  >`
                : ""}
            </summary>
            ${t.description
              ? html`<p style="color:var(--shenas-text-muted,#888);font-size:0.85rem;margin:0.3rem 0 0.5rem 1rem">
                  ${t.description}
                </p>`
              : ""}
            <table style="margin-left:1rem;font-size:0.85rem">
              <thead>
                <tr>
                  <th style="text-align:left;padding:2px 12px 2px 0">Column</th>
                  <th style="text-align:left;padding:2px 12px 2px 0">Type</th>
                  <th style="text-align:left;padding:2px 0">Description</th>
                </tr>
              </thead>
              <tbody>
                ${t.columns.map(
                  (c) => html`
                    <tr>
                      <td style="padding:2px 12px 2px 0;font-family:monospace">${c.name}</td>
                      <td style="padding:2px 12px 2px 0;color:var(--shenas-text-muted,#888)">${c.db_type}</td>
                      <td style="padding:2px 0">${c.description || ""}</td>
                    </tr>
                  `,
                )}
              </tbody>
            </table>
          </details>
        `,
      )}
    `;
  }

  _renderResourceSchema() {
    const tableMeta =
      ((this._info as unknown as Record<string, unknown>)?.table_metadata as {
        table: string;
        display_name: string;
        description: string;
        kind: string;
        rows?: number;
        earliest?: string;
        latest?: string;
        columns: { name: string; db_type: string; display_name?: string; description: string }[];
      }[]) || [];
    if (tableMeta.length === 0) {
      return html`<p style="color:var(--shenas-text-muted,#888)">No tables declared.</p>`;
    }
    return html`${tableMeta.map(
      (resource) => html`
        <details style="margin-bottom:0.8rem">
          <summary style="cursor:pointer;font-weight:600;font-size:0.9rem">
            ${resource.display_name || resource.table}
            ${resource.rows
              ? html`<span
                  style="font-weight:400;color:var(--shenas-text-muted,#888);margin-left:0.5rem;font-size:0.8rem"
                  >${resource.rows} rows</span
                >`
              : ""}
            ${resource.earliest
              ? html`<span
                  style="font-weight:400;color:var(--shenas-text-muted,#888);margin-left:0.5rem;font-size:0.8rem"
                  >${resource.earliest} - ${resource.latest}</span
                >`
              : ""}
            ${resource.kind
              ? html`<span
                  style="font-weight:400;color:var(--shenas-text-muted,#888);margin-left:0.5rem;font-size:0.8rem"
                  >${resource.kind}</span
                >`
              : ""}
          </summary>
          ${resource.description
            ? html`<p style="color:var(--shenas-text-muted,#888);font-size:0.85rem;margin:0.3rem 0 0.4rem 1rem">
                ${resource.description}
              </p>`
            : ""}
          <table style="margin-left:1rem;font-size:0.85rem;border-collapse:collapse">
            <thead>
              <tr>
                <th style="text-align:left;padding:2px 12px 2px 0">Column</th>
                <th style="text-align:left;padding:2px 12px 2px 0">Type</th>
                <th style="text-align:left;padding:2px 0">Description</th>
              </tr>
            </thead>
            <tbody>
              ${(resource.columns || []).map(
                (col) => html`
                  <tr>
                    <td style="padding:2px 12px 2px 0;font-family:monospace">${col.display_name || col.name}</td>
                    <td style="padding:2px 12px 2px 0;color:var(--shenas-text-muted,#888)">${col.db_type}</td>
                    <td style="padding:2px 0">${col.description || ""}</td>
                  </tr>
                `,
              )}
            </tbody>
          </table>
        </details>
      `,
    )}`;
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
          ${info.icon_url
            ? html`<img
                src="${info.icon_url}"
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
              >`}${info.display_name || info.name} <shenas-badge>${info.kind}</shenas-badge>${info.version
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
                      const url = new URL(window.location.href);
                      url.searchParams.set("table", this._dataTable);
                      window.history.pushState({}, "", url.toString());
                    }}
                  >
                    ${this._tables
                      .filter((table) => !table.name.startsWith("_dlt_"))
                      .map(
                        (table) =>
                          html`<option value=${table.name} ?selected=${this._dataTable === table.name}>
                            ${this._tableDisplayName(table.name)}${table.rows ? ` (${table.rows})` : ""}
                          </option>`,
                      )}
                  </select>`
                : ""}
            `
          : ""}
        ${this._info?.has_entities
          ? html`
              <a
                class="tab"
                href="${basePath}/entities"
                aria-selected=${this.activeTab === "entities"}
                @click=${(e: MouseEvent) => {
                  e.preventDefault();
                  this._switchTab("entities");
                }}
                >Entities</a
              >
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
          ? html`<shenas-auth api-base="${this.apiBase}" source-name="${this.name}"></shenas-auth>`
          : this.activeTab === "transforms"
            ? this._renderTransforms()
            : this.activeTab === "data"
              ? this._renderData()
              : this.activeTab === "entities"
                ? this._renderEntities()
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
            ${this._renderResourceSchema()}`
        : ""}
      ${this.kind === "dataset" && this._schemaTransforms.length > 0
        ? html` <h4 class="section-title">Transforms</h4>
            <shenas-data-list
              .columns=${[
                {
                  label: "Source",
                  render: (transform: SchemaTransform) =>
                    html`<span
                      style="cursor:pointer;text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                      title="${transform.source.schemaName}.${transform.source.tableName}"
                      @click=${() =>
                        this.dispatchEvent(
                          new CustomEvent("inspect-table", {
                            bubbles: true,
                            composed: true,
                            detail: { schema: transform.source.schemaName, table: transform.source.tableName },
                          }),
                        )}
                      >${transform.source.plugin?.displayName
                        ? `${transform.source.plugin.displayName} > `
                        : ""}${transform.source.displayName || transform.source.tableName}</span
                    >`,
                },
                {
                  label: "Target",
                  render: (transform: SchemaTransform) =>
                    html`<span
                      style="cursor:pointer;text-decoration:underline;text-decoration-color:var(--shenas-text-faint,#ccc)"
                      title="${transform.target.schemaName}.${transform.target.tableName}"
                      @click=${() =>
                        this.dispatchEvent(
                          new CustomEvent("inspect-table", {
                            bubbles: true,
                            composed: true,
                            detail: { schema: transform.target.schemaName, table: transform.target.tableName },
                          }),
                        )}
                      >${transform.target.displayName || transform.target.tableName}</span
                    >`,
                },
                {
                  label: "Type",
                  class: "muted",
                  render: (transform: SchemaTransform) =>
                    transform.transformTypeDisplayName || transform.transformType || "",
                },
                {
                  label: "Status",
                  render: (transform: SchemaTransform) =>
                    html`<status-toggle ?enabled=${transform.enabled}></status-toggle>`,
                },
              ]}
              .rows=${this._schemaTransforms}
              .rowClass=${(transform: SchemaTransform) => (transform.enabled ? "" : "disabled-row")}
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
        .sourceTables=${((this._info as unknown as Record<string, unknown>)?.table_metadata as { table: string }[]) ||
        []}
        .targetTables=${this.datasetTables || []}
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
    const source = this._info?.name || this.name;
    const { data } = await this._client.query({
      query: GET_SUGGESTED_DATASETS,
      variables: { source },
      fetchPolicy: "network-only",
    });
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
