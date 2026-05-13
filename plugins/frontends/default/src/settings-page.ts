import "./categories-page.ts";
import { LitElement, html, css, render } from "lit";
import {
  ApolloMutationController,
  getClient,
  gqlTag,
  openExternal,
  renderMessage,
  buttonStyles,
  formStyles,
  linkStyles,
  messageStyles,
} from "shenas-frontends";
import { GET_THEME, GET_AVAILABLE_PLUGINS } from "./graphql/queries.ts";
import { ENABLE_PLUGIN, DISABLE_PLUGIN } from "./graphql/mutations.ts";

type PluginKind = { id: string; label: string };

interface AccessTypeInfo {
  name: string;
  label: string;
  icon: string;
  description: string;
}

interface PluginSummary {
  name: string;
  displayName?: string;
  package?: string;
  version?: string;
  enabled?: boolean;
  description?: string;
  syncedAt?: string;
  hasAuth?: boolean;
  isAuthenticated?: boolean;
  accessTypes?: AccessTypeInfo[];
}

interface Message {
  type: string;
  text: string;
}

/** Map access type name to a small SVG icon. */
const _ACCESS_TYPE_ICONS: Record<string, string> = {
  official_api: "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z", // shield
  unofficial_api:
    "M20 8h-2.81c-.45-.78-1.07-1.45-1.82-1.96L17 4.41 15.59 3l-2.17 2.17C12.96 5.06 12.49 5 12 5s-.96.06-1.41.17L8.41 3 7 4.41l1.62 1.63C7.88 6.55 7.26 7.22 6.81 8H4v2h2.09c-.05.33-.09.66-.09 1v1H4v2h2v1c0 .34.04.67.09 1H4v2h2.81c1.04 1.79 2.97 3 5.19 3s4.15-1.21 5.19-3H20v-2h-2.09c.05-.33.09-.66.09-1v-1h2v-2h-2v-1c0-.34-.04-.67-.09-1H20V8z", // bug/bot
  local_files: "M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z", // file
  local_db:
    "M12 3C7.58 3 4 4.79 4 7v10c0 2.21 3.58 4 8 4s8-1.79 8-4V7c0-2.21-3.58-4-8-4zm0 2c3.87 0 6 1.5 6 2s-2.13 2-6 2-6-1.5-6-2 2.13-2 6-2zM4 17v-2.34c1.36 1.13 3.5 1.84 6 2.04v2.14c-3.43-.34-5.53-1.33-6-1.84zm8 2.84V17.7c.66.05 1.32.08 2 .08.68 0 1.34-.03 2-.08v2.14c-.65.05-1.32.08-2 .08s-1.35-.03-2-.08z", // database
  cloud_import:
    "M19.35 10.04A7.49 7.49 0 0012 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 000 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z", // cloud download
  export_file: "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z", // download
  scraping:
    "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z", // eye
  public_dataset:
    "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z", // globe
};

function _accessTypeIcon(name: string): ReturnType<typeof html> {
  const path = _ACCESS_TYPE_ICONS[name];
  if (!path) return html``;
  return html`<svg
    viewBox="0 0 24 24"
    width="16"
    height="16"
    fill="currentColor"
    style="vertical-align:middle;opacity:0.6"
  >
    <path d=${path} />
  </svg>`;
}

interface ActionInfo {
  id: string;
  label: string;
  category: string;
}

/**
 * Single source of truth for the static (non-plugin-kind) entries in the
 * settings sidebar. The plugin kinds (source/dataset/...) are appended after
 * these by both the desktop sub-nav (app-shell.ts) and the mobile burger menu.
 */
export interface SettingsNavItem {
  id: string;
  label: string;
}
export const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { id: "profile", label: "Profile" },
  { id: "entities", label: "Entities" },
  { id: "categories", label: "Categories" },
  { id: "hotkeys", label: "Hotkeys" },
];

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeKind: { type: String, attribute: "active-kind" },
    entitiesView: { type: String, attribute: "entities-view" },
    onNavigate: { type: Function },
    onPluginsChanged: { type: Function },
    onMultiuserToggle: { type: Function },
    onSwitchUser: { type: Function },
    allActions: { type: Array },
    allPlugins: { type: Object },
    pluginKinds: { type: Array },
    remoteUser: { type: Object },
    serverUrl: { type: String, attribute: "server-url" },
    deviceName: { type: String, attribute: "device-name" },
    multiuserEnabled: { type: Boolean },
    localUser: { type: Object },
    _plugins: { state: true },
    _loading: { state: true },
    _actionMessage: { state: true },
    _installing: { state: true },
    _availablePlugins: { state: true },
    _selectedPlugin: { state: true },
    _pluginKinds: { state: true },
    _menuOpen: { state: true },
  };

  static styles = [
    buttonStyles,
    formStyles,
    linkStyles,
    messageStyles,
    css`
      :host {
        display: block;
        height: 100%;
      }
      .layout {
        display: flex;
        gap: 2rem;
        height: 100%;
      }
      .sidebar {
        min-width: 140px;
        flex-shrink: 0;
        overflow-y: auto;
      }
      .sidebar ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .sidebar-section {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
        padding: 0.8rem 0.8rem 0.3rem;
      }
      .sidebar li {
        margin: 0;
      }
      .sidebar a {
        display: block;
        width: 100%;
        text-align: left;
        padding: 0.5rem 0.8rem;
        border: none;
        background: none;
        cursor: pointer;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        border-radius: 4px;
        border-left: 3px solid transparent;
      }
      .sidebar a:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .sidebar a[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
        border-left-color: var(--shenas-primary, #0066cc);
      }
      .content {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
      }
      .content h3 {
        font-size: 1rem;
        margin: 0 0 1rem;
      }
      /* Burger menu button (hidden on desktop) */
      .burger {
        display: none;
        background: none;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 6px;
        padding: 0.4rem 0.6rem;
        cursor: pointer;
        color: var(--shenas-text-secondary, #666);
        margin-bottom: 0.5rem;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
      }
      .burger svg {
        flex-shrink: 0;
      }
      /* Overlay menu (mobile) */
      .menu-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.3);
        z-index: 100;
      }
      .menu-overlay.open {
        display: block;
      }
      .menu-panel {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        width: 220px;
        background: var(--shenas-bg, #fff);
        z-index: 101;
        padding: 1rem;
        overflow-y: auto;
        box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
      }
      .menu-panel .menu-close {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 1.2rem;
        color: var(--shenas-text-muted, #888);
        float: right;
      }
      .menu-panel a {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem 0.5rem;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
      }
      .menu-panel a:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .menu-panel a[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .menu-panel a svg {
        flex-shrink: 0;
      }
      .menu-panel .sidebar-section {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
        padding: 0.8rem 0.5rem 0.3rem;
      }
      .profile {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-width: 480px;
      }
      .profile-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.6rem 0.8rem;
        background: var(--shenas-bg-secondary, #f3f0eb);
        border: 1px solid var(--shenas-border, #d8d4cc);
        border-radius: 6px;
      }
      .profile-label {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
      }
      .profile-value {
        font-size: 0.9rem;
        color: var(--shenas-text, #222);
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }
      .profile .device-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--shenas-text-muted, #888);
      }
      .profile .device-dot.connected {
        background: var(--shenas-success, #628261);
      }
      .profile-actions {
        margin-top: 0.5rem;
      }
      @media (max-width: 768px) {
        .sidebar {
          display: none;
        }
        .burger {
          display: flex;
        }
        .layout {
          gap: 0;
          flex-direction: column;
        }
        .content {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
        }
      }
    `,
  ];

  declare apiBase: string;
  declare activeKind: string;
  declare entitiesView: string;
  declare onNavigate: ((kind: string) => void) | null;
  declare onPluginsChanged: ((data: Record<string, PluginSummary[]>) => void) | null;
  declare onMultiuserToggle: ((enabled: boolean) => void) | null;
  declare onSwitchUser: (() => void) | null;
  declare allActions: ActionInfo[];
  declare allPlugins: Record<string, PluginSummary[]>;
  declare pluginKinds: PluginKind[];
  declare remoteUser: Record<string, unknown> | null;
  declare serverUrl: string;
  declare deviceName: string;
  declare multiuserEnabled: boolean;
  declare localUser: { id: number; username: string } | null;
  declare _plugins: Record<string, PluginSummary[]>;
  declare _schemaStats: Record<string, { totalRows: number; earliest: string; latest: string }>;
  declare _loading: boolean;
  declare _actionMessage: Message | null;
  declare _installing: boolean;
  declare _availablePlugins: string[] | null;
  declare _selectedPlugin: string;
  declare _menuOpen: boolean;
  declare _pluginKinds: PluginKind[];

  private _enablePluginMutation = new ApolloMutationController(this, ENABLE_PLUGIN, { client: getClient() });
  private _disablePluginMutation = new ApolloMutationController(this, DISABLE_PLUGIN, { client: getClient() });

  constructor() {
    super();
    this.apiBase = "/api";
    this.activeKind = "profile";
    this.entitiesView = "";
    this.onNavigate = null;
    this.onPluginsChanged = null;
    this.onMultiuserToggle = null;
    this.onSwitchUser = null;
    this.allActions = [];
    this.allPlugins = {};
    this.pluginKinds = [];
    this.remoteUser = null;
    this.serverUrl = "https://shenas.ai";
    this.deviceName = "";
    this.multiuserEnabled = false;
    this.localUser = null;
    this._plugins = {};
    this._schemaStats = {};
    this._loading = true;
    this._actionMessage = null;
    this._installing = false;
    this._availablePlugins = null;
    this._selectedPlugin = "";
    this._menuOpen = false;
    this._pluginKinds = [];
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._pluginKinds = [...(this.pluginKinds || [])].sort((a, b) => a.label.localeCompare(b.label));
    // Show cached sidebar data immediately if available.
    if (this.allPlugins && Object.keys(this.allPlugins).length > 0) {
      this._plugins = this.allPlugins;
    }
    // Only fetch full plugin data when viewing a plugin kind tab
    // (source/dataset/etc.), not for entities/categories/profile/hotkeys.
    const isPluginKind = this._pluginKinds.some((k) => k.id === this.activeKind);
    if (!isPluginKind) {
      this._loading = false;
      return;
    }
    if (Object.keys(this._plugins).length > 0) {
      this._loading = false;
      this._fetchAll({ background: true });
    } else {
      this._fetchAll();
    }
  }

  async _fetchAll(_options?: { force?: boolean; background?: boolean }): Promise<void> {
    if (!_options?.background) this._loading = true;
    this._pluginKinds = [...(this.pluginKinds || [])].sort((a, b) => a.label.localeCompare(b.label));
    const baseFields = `name displayName package version enabled description hasAuth isAuthenticated`;
    const sourceFields = `${baseFields} syncedAt totalRows accessTypes { name label icon description }`;
    const kindQueries = this._pluginKinds
      .map(({ id }) => `${id}: plugins(kind: "${id}", full: true) { ${id === "source" ? sourceFields : baseFields} }`)
      .join("\n      ");
    if (!kindQueries) {
      this._plugins = {};
      this._schemaStats = {};
      this._loading = false;
      return;
    }
    try {
      const { data } = await getClient().query({
        query: gqlTag([`{ ${kindQueries} }`] as unknown as TemplateStringsArray),
        fetchPolicy: "network-only",
      });
      const result: Record<string, PluginSummary[]> = {};
      for (const { id } of this._pluginKinds) {
        result[id] = (data?.[id] as PluginSummary[]) || [];
      }
      this._plugins = result;
      // Build per-plugin stats from totalRows field
      const schemaStats: Record<string, { totalRows: number; earliest: string; latest: string }> = {};
      for (const plugins of Object.values(result)) {
        for (const plugin of plugins) {
          const rows = (plugin as unknown as { totalRows?: number }).totalRows || 0;
          if (rows > 0) {
            schemaStats[plugin.name] = { totalRows: rows, earliest: "", latest: "" };
          }
        }
      }
      this._schemaStats = schemaStats;
      if (this.onPluginsChanged) this.onPluginsChanged(result);
    } catch (error) {
      console.error("Failed to load plugins:", error);
      this._actionMessage = { type: "error", text: "Failed to load plugins" };
    } finally {
      this._loading = false;
    }
  }

  async _togglePlugin(kind: string, name: string, currentlyEnabled: boolean): Promise<void> {
    const action = currentlyEnabled ? "disable" : "enable";
    const controller = action === "enable" ? this._enablePluginMutation : this._disablePluginMutation;
    const { data } = await controller.mutate({ variables: { k: kind, n: name } });
    const result = (action === "enable" ? data?.enablePlugin : data?.disablePlugin) as
      | Record<string, unknown>
      | undefined;
    if (!result?.ok) {
      this._actionMessage = { type: "error", text: (result?.message as string) || `${action} failed` };
    }
    if (kind === "theme") {
      await this._applyActiveTheme();
    }
    if (kind === "frontend") {
      window.location.replace(window.location.pathname + "?_switch=" + Date.now());
      return;
    }
    this.dispatchEvent(new CustomEvent("plugin-state-changed", { bubbles: true, composed: true }));
    await this._fetchAll({ force: true });
  }

  async _applyActiveTheme(): Promise<void> {
    const result = await getClient().query({ query: GET_THEME, fetchPolicy: "network-only" });
    const data = result?.data as Record<string, unknown> | undefined;
    if (!data?.theme) return;
    const { css } = data.theme as Record<string, string>;
    let link = document.querySelector("link[data-shenas-theme]") as HTMLLinkElement | null;
    if (css) {
      if (!link) {
        link = document.createElement("link");
        link.rel = "stylesheet";
        link.setAttribute("data-shenas-theme", "");
        document.head.appendChild(link);
      }
      link.href = css;
    } else if (link) {
      link.remove();
    }
  }

  async _startInstall(kind: string): Promise<void> {
    this._installing = true;
    this._selectedPlugin = "";
    this._availablePlugins = null;
    const result = await getClient().query({
      query: GET_AVAILABLE_PLUGINS,
      variables: { kind },
      fetchPolicy: "network-only",
    });
    const available = ((result?.data as Record<string, unknown>)?.availablePlugins as string[]) || [];
    const installed = new Set((this._plugins[kind] || []).map((p) => p.name));
    this._availablePlugins = available.filter((n) => !installed.has(n));

    // Build form panel and dispatch to app-shell's right panel
    const label = this._pluginKinds.find((k) => k.id === kind)?.label || kind.charAt(0).toUpperCase() + kind.slice(1);
    const panel = document.createElement("div");
    panel.style.padding = "1rem";
    this._renderInstallPanel(panel, kind, label);
    this.dispatchEvent(
      new CustomEvent("show-panel", { bubbles: true, composed: true, detail: { component: panel, width: 340 } }),
    );
  }

  _renderInstallPanel(container: HTMLElement, kind: string, label: string): void {
    const plugins = this._availablePlugins;
    const singular = label.endsWith("s") ? label.slice(0, -1) : label;

    const pluginOptions = (plugins || []).map((n) => ({
      value: n,
      label: this._displayPluginName(n),
    }));

    render(
      html`
        <shenas-form-panel
          title="Add ${singular}"
          submit-label="Add"
          @submit=${() => this._install(kind)}
          @cancel=${() => {
            this._installing = false;
            this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
          }}
        >
          ${plugins === null
            ? html`<p style="color:#888">Loading available plugins...</p>`
            : plugins.length === 0
              ? html`<p style="color:#888">No new ${label.toLowerCase()} available</p>`
              : html`<shenas-dropdown
                  label=""
                  placeholder="Select a ${singular.toLowerCase()}..."
                  .options=${pluginOptions}
                  value=${this._selectedPlugin}
                  @change=${(e: CustomEvent) => {
                    this._selectedPlugin = e.detail.value;
                  }}
                ></shenas-dropdown>`}
        </shenas-form-panel>
      `,
      container,
    );
  }

  async _install(kind: string): Promise<void> {
    const name = this._selectedPlugin;
    if (!name) return;
    this._actionMessage = null;
    this._installing = false;
    this.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
    const displayName = this._displayPluginName(name);
    const jobId = `install-${kind}-${name}-${Date.now()}`;

    this.dispatchEvent(
      new CustomEvent("job-start", {
        bubbles: true,
        composed: true,
        detail: { id: jobId, label: `Adding ${displayName}` },
      }),
    );

    const result = await this._streamJob(jobId, `${this.apiBase}/plugins/${kind}/install-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names: [name], skip_verify: true }),
    });

    if (result?.ok) {
      this._actionMessage = { type: "success", text: result.message };
      await this._fetchAll();
    } else {
      this._actionMessage = { type: "error", text: result?.message || "Add failed" };
    }
  }

  async _streamJob(
    jobId: string,
    url: string,
    fetchOptions: RequestInit,
  ): Promise<{ ok: boolean; message: string } | null> {
    try {
      const resp = await fetch(url, fetchOptions);
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: { ok: boolean; message: string } | null = null;

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
                new CustomEvent("job-log", {
                  bubbles: true,
                  composed: true,
                  detail: { id: jobId, text: evt.text },
                }),
              );
            } else if (evt.event === "done") {
              finalResult = { ok: evt.ok as boolean, message: evt.message as string };
              this.dispatchEvent(
                new CustomEvent("job-finish", {
                  bubbles: true,
                  composed: true,
                  detail: { id: jobId, ok: evt.ok, message: evt.message },
                }),
              );
            }
          } catch {
            /* skip malformed lines */
          }
        }
      }
      return finalResult;
    } catch (err) {
      const error = err as Error;
      this.dispatchEvent(
        new CustomEvent("job-finish", {
          bubbles: true,
          composed: true,
          detail: { id: jobId, ok: false, message: error.message },
        }),
      );
      return { ok: false, message: error.message };
    }
  }

  _displayPluginName(name: string): string {
    return name
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  _switchKind(kind: string): void {
    this.activeKind = kind;
    this._menuOpen = false;
    if (this.onNavigate) this.onNavigate(kind);
  }

  _displayName(): string {
    if (this.activeKind === "profile") return "Profile";
    if (this.activeKind === "entities") return "Entities";
    if (this.activeKind === "categories") return "Categories";
    if (this.activeKind === "hotkeys") return "Hotkeys";
    const kind = this._pluginKinds.find((k) => k.id === this.activeKind);
    return kind?.label || this.activeKind.charAt(0).toUpperCase() + this.activeKind.slice(1);
  }

  render() {
    return html`
      <button
        class="burger"
        @click=${() => {
          this._menuOpen = !this._menuOpen;
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
        ${this._displayName()}
      </button>
      ${this._menuOpen
        ? html`
            <div
              class="menu-overlay"
              @click=${() => {
                this._menuOpen = false;
              }}
            ></div>
            <div class="menu-panel">
              ${SETTINGS_NAV_ITEMS.map(
                (item) => html`
                  <a
                    href="/settings/${item.id}"
                    aria-selected=${this.activeKind === item.id}
                    @click=${(e: MouseEvent) => {
                      e.preventDefault();
                      this._switchKind(item.id);
                    }}
                    >${item.label}</a
                  >
                `,
              )}
              <span class="sidebar-section">Plugins</span>
              ${this._pluginKinds.map(
                ({ id, label }) => html`
                  <a
                    href="/settings/${id}"
                    aria-selected=${this.activeKind === id}
                    @click=${(e: MouseEvent) => {
                      e.preventDefault();
                      this._switchKind(id);
                    }}
                    >${label}</a
                  >
                `,
              )}
            </div>
          `
        : ""}
      <shenas-page ?loading=${this._loading} loading-text="Loading plugins..." display-name="${this._displayName()}">
        ${renderMessage(this._actionMessage)}
        ${this.activeKind === "profile"
          ? this._renderProfile()
          : this.activeKind === "entities"
            ? html`<shenas-entities
                api-base="${this.apiBase}"
                active-view="${this.entitiesView || "entities"}"
              ></shenas-entities>`
            : this.activeKind === "categories"
              ? html`<shenas-categories api-base="${this.apiBase}"></shenas-categories>`
              : this.activeKind === "hotkeys"
                ? html`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions || []}></shenas-hotkeys>`
                : this._renderKind(this.activeKind)}
      </shenas-page>
    `;
  }

  _renderProfile() {
    const user = this.remoteUser;
    const name = user ? (user.name as string) || (user.email as string) || "" : "";
    const email = user ? (user.email as string) || "" : "";

    const multiuserSection = html`
      <div class="profile-row">
        <div>
          <span class="profile-label">Multi-user mode</span>
          <span
            class="profile-value"
            style="font-size:0.8rem;color:var(--shenas-text-muted,#888);display:block;margin-top:2px"
          >
            Enable multiple local users on this device
          </span>
        </div>
        <label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer">
          <input
            type="checkbox"
            ?checked=${this.multiuserEnabled}
            @change=${(e: Event) => {
              const enabled = (e.target as HTMLInputElement).checked;
              if (this.onMultiuserToggle) this.onMultiuserToggle(enabled);
            }}
          />
          ${this.multiuserEnabled ? "On" : "Off"}
        </label>
      </div>
      ${this.multiuserEnabled && this.localUser
        ? html`
            <div class="profile-row">
              <div>
                <span class="profile-label">Local user</span>
                <span class="profile-value">${this.localUser.username}</span>
              </div>
              <button
                @click=${() => {
                  if (this.onSwitchUser) this.onSwitchUser();
                }}
              >
                Switch User
              </button>
            </div>
          `
        : ""}
    `;

    if (!user) {
      return html`
        <div class="profile">
          ${multiuserSection}
          <p>You are not signed in to shenas.net.</p>
          <button @click=${() => (window.location.href = "/api/auth/login")}>Sign in with shenas.net</button>
        </div>
      `;
    }
    return html`
      <div class="profile">
        ${multiuserSection}
        <div class="profile-row">
          <span class="profile-label">Name</span>
          <span class="profile-value">${name}</span>
        </div>
        ${email && email !== name
          ? html`<div class="profile-row">
              <span class="profile-label">Email</span>
              <span class="profile-value">${email}</span>
            </div>`
          : ""}
        <div class="profile-row">
          <span class="profile-label">Device</span>
          <span class="profile-value">
            <span class="device-dot connected"></span>
            ${this.deviceName || "this device"}
          </span>
        </div>
        <div class="profile-actions">
          <button @click=${() => openExternal(`${this.serverUrl}/dashboard`)}>Dashboard</button>
          <button
            class="danger"
            @click=${async () => {
              await fetch("/api/auth/logout", { method: "POST" });
              this.remoteUser = null;
              this._actionMessage = { type: "success", text: "Logged out from shenas.net" };
              this.dispatchEvent(new CustomEvent("auth-changed", { bubbles: true, composed: true }));
            }}
          >
            Logout
          </button>
        </div>
      </div>
    `;
  }

  _formatFreq(m: number): string {
    if (m >= 1440 && m % 1440 === 0) return `${m / 1440}d`;
    if (m >= 60 && m % 60 === 0) return `${m / 60}h`;
    if (m >= 1) return `${m}m`;
    return `${m * 60}s`;
  }

  _renderKind(kind: string) {
    const plugins = this._plugins[kind] || [];
    const label = this._pluginKinds.find((k) => k.id === kind)?.label || kind.charAt(0).toUpperCase() + kind.slice(1);
    return html`
      <h3>${label}</h3>
      <shenas-data-list
        .columns=${[
          {
            label: "Name",
            render: (p: PluginSummary) => html`<a href="/settings/${kind}/${p.name}">${p.displayName || p.name}</a>`,
          },
          ...(kind === "source"
            ? [
                {
                  label: "Access",
                  render: (p: PluginSummary) =>
                    html`${(p.accessTypes || []).map(
                      (at) =>
                        html`<span title="${at.label}: ${at.description}" style="margin-right:2px"
                          >${_accessTypeIcon(at.name)}</span
                        >`,
                    )}`,
                },
                {
                  label: "Data",
                  render: (p: PluginSummary) => {
                    const s = this._schemaStats[p.name];
                    if (!s || !s.totalRows) return html`<span class="muted">--</span>`;
                    const rows =
                      s.totalRows >= 1_000_000
                        ? `${(s.totalRows / 1_000_000).toFixed(1)}M`
                        : s.totalRows >= 1_000
                          ? `${(s.totalRows / 1_000).toFixed(1)}k`
                          : `${s.totalRows}`;
                    const range =
                      s.earliest && s.latest ? `${s.earliest.slice(0, 10)} -- ${s.latest.slice(0, 10)}` : "";
                    return html`${rows}
                    rows${range ? html`<br /><span class="muted" style="font-size:0.75rem">${range}</span>` : ""}`;
                  },
                },
                {
                  label: "Last Synced",
                  class: "mono",
                  render: (p: PluginSummary) => (p.syncedAt ? p.syncedAt.slice(0, 16).replace("T", " ") : "never"),
                },
              ]
            : []),
          {
            label: "Status",
            render: (p: PluginSummary) =>
              p.hasAuth && p.isAuthenticated === false
                ? html`<span style="color:var(--shenas-error,#c62828);font-size:0.8rem">Needs Auth</span>`
                : html`<status-toggle
                    ?enabled=${p.enabled !== false}
                    toggleable
                    @toggle=${() => this._togglePlugin(kind, p.name, p.enabled !== false)}
                  ></status-toggle>`,
          },
        ]}
        .rows=${plugins}
        .rowClass=${(p: PluginSummary) => (p.enabled === false ? "disabled-row" : "")}
        ?show-add=${true}
        @add=${() => this._startInstall(kind)}
        empty-text="No ${label.toLowerCase()} added"
      ></shenas-data-list>
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
