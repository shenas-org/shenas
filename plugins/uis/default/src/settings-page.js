import { LitElement, html, css } from "lit";
import { gql, gqlFull, renderMessage } from "./api.js";
import { PLUGIN_KINDS } from "./constants.js";
import { buttonStyles, formStyles, linkStyles, messageStyles } from "./shared-styles.js";

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeKind: { type: String, attribute: "active-kind" },
    onNavigate: { type: Function },
    onPluginsChanged: { type: Function },
    allActions: { type: Array },
    allPlugins: { type: Object },
    schemaPlugins: { type: Object },
    _plugins: { state: true },
    _loading: { state: true },
    _actionMessage: { state: true },
    _installing: { state: true },
    _availablePlugins: { state: true },
    _selectedPlugin: { state: true },
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
      .burger svg { flex-shrink: 0; }
      /* Overlay menu (mobile) */
      .menu-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.3);
        z-index: 100;
      }
      .menu-overlay.open { display: block; }
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
        box-shadow: 2px 0 8px rgba(0,0,0,0.15);
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
      .menu-panel a svg { flex-shrink: 0; }
      .menu-panel .sidebar-section {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
        padding: 0.8rem 0.5rem 0.3rem;
      }
      @media (max-width: 768px) {
        .sidebar { display: none; }
        .burger { display: flex; }
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

  constructor() {
    super();
    this.apiBase = "/api";
    this.activeKind = "data-flow";
    this.onNavigate = null;
    this._plugins = {};
    this._loading = true;
    this._actionMessage = null;
    this._installing = false;
    this._menuOpen = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll() {
    this._loading = true;
    const data = await gql(this.apiBase, `{
      pipes: plugins(kind: "pipe") { name displayName package version enabled description syncedAt hasAuth }
      schemas: plugins(kind: "schema") { name displayName package version enabled description }
      componentPlugins: plugins(kind: "component") { name displayName package version enabled description }
      uis: plugins(kind: "ui") { name displayName package version enabled description }
      themes: plugins(kind: "theme") { name displayName package version enabled description }
    }`);
    const result = {
      pipe: data?.pipes || [],
      schema: data?.schemas || [],
      component: data?.componentPlugins || [],
      ui: data?.uis || [],
      theme: data?.themes || [],
    };
    this._plugins = result;
    this._loading = false;
    if (this.onPluginsChanged) this.onPluginsChanged(result);
  }



  async _togglePlugin(kind, name, currentlyEnabled) {
    const action = currentlyEnabled ? "disable" : "enable";
    const mutation = action === "enable"
      ? `mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok message } }`
      : `mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok message } }`;
    const { data } = await gqlFull(this.apiBase, mutation, { k: kind, n: name });
    const result = action === "enable" ? data?.enablePlugin : data?.disablePlugin;
    if (!result?.ok) {
      this._actionMessage = { type: "error", text: result?.message || `${action} failed` };
    }
    if (kind === "theme") {
      await this._applyActiveTheme();
    }
    await this._fetchAll({ force: true });
  }

  async _applyActiveTheme() {
    const data = await gql(this.apiBase, `{ theme { css } }`);
    if (!data?.theme) return;
    const { css } = data.theme;
    let link = document.querySelector('link[data-shenas-theme]');
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

  async _startInstall(kind) {
    this._installing = true;
    this._selectedPlugin = "";
    this._availablePlugins = null;
    const data = await gql(this.apiBase, `query($kind: String!) { availablePlugins(kind: $kind) }`, { kind });
    const available = data?.availablePlugins || [];
    const installed = new Set((this._plugins[kind] || []).map((p) => p.name));
    this._availablePlugins = available.filter((n) => !installed.has(n));
  }

  async _install(kind) {
    const name = this._selectedPlugin;
    if (!name) return;
    this._actionMessage = null;
    const { data } = await gqlFull(this.apiBase, `mutation($kind: String!, $names: [String!]!) { installPlugins(kind: $kind, names: $names, skipVerify: true) { results { name ok message } } }`, { kind, names: [name] });
    const result = data?.installPlugins?.results?.[0];
    if (result?.ok) {
      this._actionMessage = { type: "success", text: result.message };
      this._installing = false;
      await this._fetchAll({ force: true });
    } else {
      this._actionMessage = {
        type: "error",
        text: result?.message || "Add failed",
      };
    }
  }

  _displayPluginName(name) {
    return name.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  }

  _switchKind(kind) {
    this.activeKind = kind;
    this._menuOpen = false;
    if (this.onNavigate) this.onNavigate(kind);
  }

  _displayName() {
    if (this.activeKind === "data-flow") return "Data Flow";
    if (this.activeKind === "hotkeys") return "Hotkeys";
    const kind = PLUGIN_KINDS.find((k) => k.id === this.activeKind);
    return kind ? kind.label : this.activeKind;
  }

  render() {
    return html`
      <shenas-page ?loading=${this._loading} loading-text="Loading plugins..." display-name="${this._displayName()}">
        ${renderMessage(this._actionMessage)}
        ${this.activeKind === "data-flow"
          ? html`<shenas-pipeline-overview api-base="${this.apiBase}" .allPlugins=${this.allPlugins} .schemaPlugins=${this.schemaPlugins}></shenas-pipeline-overview>`
          : this.activeKind === "hotkeys"
            ? html`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions || []}></shenas-hotkeys>`
            : this._renderKind(this.activeKind)}
      </shenas-page>
    `;
  }

  _formatFreq(m) {
    if (m >= 1440 && m % 1440 === 0) return `${m / 1440}d`;
    if (m >= 60 && m % 60 === 0) return `${m / 60}h`;
    if (m >= 1) return `${m}m`;
    return `${m * 60}s`;
  }

  _renderKind(kind) {
    const plugins = this._plugins[kind] || [];
    const label = PLUGIN_KINDS.find((k) => k.id === kind)?.label || kind;
    return html`
      <h3>${label}</h3>
      <shenas-data-list
        .columns=${[
          { label: "Name", render: (p) => html`<a href="/settings/${kind}/${p.name}">${p.displayName || p.name}</a>` },
          ...(kind === "pipe" ? [
            { label: "Last Synced", class: "mono", render: (p) => p.syncedAt ? p.syncedAt.slice(0, 16).replace("T", " ") : "never" },
          ] : []),
          { label: "Status", render: (p) => kind === "pipe" && p.hasAuth === false
            ? html`<span style="color:var(--shenas-error,#c62828);font-size:0.8rem">Needs Auth</span>`
            : html`<status-toggle ?enabled=${p.enabled !== false} toggleable @toggle=${() => this._togglePlugin(kind, p.name, p.enabled !== false)}></status-toggle>` },
        ]}
        .rows=${plugins}
        .rowClass=${(p) => p.enabled === false ? "disabled-row" : ""}
        ?show-add=${!this._installing}
        @add=${() => this._startInstall(kind)}
        empty-text="No ${label.toLowerCase()} added"
      ></shenas-data-list>
      ${this._installing
        ? html`<shenas-form-panel
            title="Add ${label.slice(0, -1)}"
            submit-label="Add"
            @submit=${() => this._install(kind)}
            @cancel=${() => { this._installing = false; }}
          >
            <div class="field">
              ${this._availablePlugins === null
                ? html`<span style="color:var(--shenas-text-muted)">Loading available plugins...</span>`
                : this._availablePlugins.length === 0
                  ? html`<span style="color:var(--shenas-text-muted)">No new ${label.toLowerCase()} available</span>`
                  : html`<select
                      @change=${(e) => { this._selectedPlugin = e.target.value; }}
                      style="width:100%;padding:0.5rem;border:1px solid var(--shenas-border-input,#ddd);border-radius:6px;font-size:0.9rem"
                    >
                      <option value="">Select a ${label.slice(0, -1).toLowerCase()}...</option>
                      ${this._availablePlugins.map((n) => html`<option value=${n}>${this._displayPluginName(n)}</option>`)}
                    </select>`}
            </div>
          </shenas-form-panel>`
        : ""}
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
