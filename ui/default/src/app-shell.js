import { LitElement, html, css } from "lit";
import { Router } from "@lit-labs/router";
import { apiFetch } from "./api.js";
import { PLUGIN_KINDS } from "./constants.js";
import { linkStyles, utilityStyles } from "./shared-styles.js";

class ShenasApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _components: { state: true },
    _loading: { state: true },
    _loadedScripts: { state: true },
    _leftWidth: { state: true },
    _rightWidth: { state: true },
    _dbStatus: { state: true },
    _inspectTable: { state: true },
    _inspectRows: { state: true },
    _paletteOpen: { state: true },
    _paletteCommands: { state: true },
    _navPaletteOpen: { state: true },
    _navCommands: { state: true },
    _tabs: { state: true },
    _activeTabId: { state: true },
  };

  _router = new Router(this, [
    { path: "/", render: () => this._renderDynamicHome() },
    { path: "/settings", render: () => this._renderSettings("overview") },
    {
      path: "/settings/:kind",
      render: ({ kind }) => this._renderSettings(kind),
    },
    {
      path: "/settings/:kind/:name",
      render: ({ kind, name }) => this._renderPluginDetail(kind, name),
    },
    {
      path: "/settings/:kind/:name/config",
      render: ({ kind, name }) => this._renderPluginDetail(kind, name, "config"),
    },
    {
      path: "/settings/:kind/:name/auth",
      render: ({ kind, name }) => this._renderPluginDetail(kind, name, "auth"),
    },
    { path: "/:tab", render: ({ tab }) => this._renderDynamicTab(tab) },
  ]);

  static styles = [
    linkStyles,
    utilityStyles,
    css`
      :host {
        display: block;
        height: 100vh;
        color: var(--shenas-text, #222);
      }
      .layout {
        display: flex;
        height: 100%;
      }
      .panel-left {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
      }
      .panel-middle {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .tab-bar {
        display: flex;
        align-items: flex-end;
        background: var(--shenas-bg-secondary, #fafafa);
        border-bottom: 1px solid var(--shenas-border, #e0e0e0);
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-width: none;
        flex-shrink: 0;
        padding: 0 4px;
        min-height: 36px;
      }
      .tab-bar::-webkit-scrollbar {
        display: none;
      }
      .tab-item {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        cursor: pointer;
        white-space: nowrap;
        user-select: none;
        border-radius: 8px 8px 0 0;
        margin-bottom: -1px;
        border: 1px solid transparent;
        border-bottom: none;
        position: relative;
      }
      .tab-item:hover {
        color: var(--shenas-text-secondary, #666);
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .tab-item.active {
        color: var(--shenas-text, #222);
        background: var(--shenas-bg, #fff);
        border-color: var(--shenas-border, #e0e0e0);
        font-weight: 500;
      }
      .tab-close {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.65rem;
        width: 16px;
        height: 16px;
        padding: 0;
        line-height: 1;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.1s;
      }
      .tab-item:hover .tab-close,
      .tab-item.active .tab-close {
        opacity: 1;
      }
      .tab-close:hover {
        color: var(--shenas-text, #222);
        background: var(--shenas-border-light, #f0f0f0);
      }
      .tab-add {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.85rem;
        padding: 6px 8px;
        line-height: 1;
        border-radius: 4px;
        margin-bottom: 2px;
      }
      .tab-add:hover {
        color: var(--shenas-text, #222);
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .tab-content {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem 2rem;
      }
      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        color: var(--shenas-text-faint, #aaa);
      }
      .empty-state img {
        width: 128px;
        height: 128px;
        opacity: 0.3;
      }
      .empty-state p {
        font-size: 0.9rem;
      }
      .panel-right {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-left: 1px solid var(--shenas-border, #e0e0e0);
      }
      .divider {
        width: 4px;
        cursor: col-resize;
        background: transparent;
        flex-shrink: 0;
      }
      .divider:hover,
      .divider.dragging {
        background: var(--shenas-border, #e0e0e0);
      }
      .header {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        margin-bottom: 1.5rem;
      }
      .header img {
        width: 64px;
        height: 64px;
      }
      .header h1 {
        margin: 0;
        font-size: 1.2rem;
      }
      .nav {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .nav-item {
        display: block;
        padding: 0.5rem 0.8rem;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        border: none;
        background: none;
        cursor: pointer;
        text-align: left;
      }
      .nav-item:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .nav-item[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .component-host {
        height: calc(100vh - 4rem);
      }
      .db-section h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: var(--shenas-text-muted, #888);
        letter-spacing: 0.05em;
        margin: 1rem 0 0.4rem;
      }
      .db-section h4:first-child {
        margin-top: 0;
      }
      .db-meta {
        font-size: 0.8rem;
        color: var(--shenas-text-secondary, #666);
        margin: 0 0 0.8rem;
      }
      .db-meta code {
        background: var(--shenas-border-light, #f0f0f0);
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 0.75rem;
      }
      .db-table-row {
        display: flex;
        justify-content: space-between;
        padding: 0.2rem 0;
        font-size: 0.8rem;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
      }
      .db-table-row:last-child {
        border-bottom: none;
      }
      .db-table-name {
        color: var(--shenas-text, #222);
      }
      .db-table-count {
        color: var(--shenas-text-muted, #888);
        font-size: 0.75rem;
      }
      .db-date-range {
        font-size: 0.7rem;
        color: var(--shenas-text-faint, #aaa);
        display: block;
      }
      .inspect-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
      }
      .inspect-header h4 {
        margin: 0;
        font-size: 0.85rem;
        color: var(--shenas-text, #222);
        text-transform: none;
        letter-spacing: normal;
      }
      .inspect-close {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-muted, #888);
        font-size: 1rem;
        padding: 0;
        line-height: 1;
      }
      .inspect-close:hover {
        color: var(--shenas-text, #222);
      }
      .inspect-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.7rem;
        table-layout: auto;
      }
      .inspect-table th {
        text-align: left;
        padding: 0.25rem 0.4rem;
        color: var(--shenas-text-secondary, #666);
        font-weight: 500;
        border-bottom: 1px solid var(--shenas-border, #e0e0e0);
        white-space: nowrap;
      }
      .inspect-table td {
        padding: 0.2rem 0.4rem;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this._components = [];
    this._loading = true;
    this._loadedScripts = new Set();
    this._elementCache = new Map();
    this._leftWidth = 160;
    this._rightWidth = 220;
    this._dbStatus = null;
    this._inspectTable = null;
    this._inspectRows = null;
    this._paletteOpen = false;
    this._paletteCommands = [];
    this._navPaletteOpen = false;
    this._navCommands = [];
    this._registeredCommands = new Map();
    this._tabs = [];
    this._activeTabId = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this.addEventListener("plugin-state-changed", () => this._refreshComponents());
    this.addEventListener("inspect-table", (e) => this._inspect(e.detail.schema, e.detail.table));
    this.addEventListener("navigate", (e) => this._navigateTo(e.detail.path, e.detail.label));
    this.addEventListener("register-command", (e) => {
      const { componentId, commands } = e.detail;
      if (!commands || commands.length === 0) {
        this._registeredCommands.delete(componentId);
      } else {
        this._registeredCommands.set(componentId, commands);
      }
    });
    this._keyHandler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "p") {
        e.preventDefault();
        this._togglePalette();
      } else if ((e.ctrlKey || e.metaKey) && e.key === "o") {
        e.preventDefault();
        this._toggleNavPalette();
      } else if ((e.ctrlKey || e.metaKey) && e.key === "w") {
        e.preventDefault();
        if (this._activeTabId != null) this._closeTab(this._activeTabId);
      } else if ((e.ctrlKey || e.metaKey) && e.key === "t") {
        e.preventDefault();
        this._addTab();
      }
    };
    document.addEventListener("keydown", this._keyHandler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener("keydown", this._keyHandler);
  }

  _togglePalette() {
    if (this._paletteOpen) {
      this._paletteOpen = false;
      return;
    }
    this._navPaletteOpen = false;
    this._buildCommands();
    this._paletteOpen = true;
  }

  async _toggleNavPalette() {
    if (this._navPaletteOpen) {
      this._navPaletteOpen = false;
      return;
    }
    this._paletteOpen = false;
    await this._buildNavCommands();
    this._navPaletteOpen = true;
  }

  async _buildNavCommands() {
    const commands = [];

    // Components (top-level tabs)
    for (const c of this._components) {
      commands.push({ id: `nav:${c.name}`, category: "Page", label: c.display_name || c.name, path: `/${c.name}` });
    }

    // Settings sections from shared PLUGIN_KINDS
    commands.push({ id: "nav:dataflow", category: "Settings", label: "Data Flow", path: "/settings/overview" });
    for (const k of PLUGIN_KINDS) {
      commands.push({ id: `nav:settings:${k.id}`, category: "Settings", label: k.label, path: `/settings/${k.id}` });
    }

    // Fetch all plugin kinds for detail page navigation
    let allPlugins = [];
    try {
      const results = await Promise.all(
        PLUGIN_KINDS.map(async (k) => {
          const data = await this._fetch(`/plugins/${k.id}`);
          return (data || []).map((p) => ({ ...p, kind: k.id, kindLabel: k.label }));
        }),
      );
      allPlugins = results.flat();
    } catch { /* use empty */ }

    for (const p of allPlugins) {
      commands.push({
        id: `nav:${p.kind}:${p.name}`,
        category: p.kindLabel,
        label: p.display_name || p.name,
        path: `/settings/${p.kind}/${p.name}`,
      });
    }

    this._navCommands = commands;
  }

  async _registerGlobalCommands() {
    const commands = [];
    try {
      for (const k of PLUGIN_KINDS) {
        const plugins = (await this._fetch(`/plugins/${k.id}`)) || [];
        for (const p of plugins) {
          const name = p.display_name || p.name;
          const enabled = p.enabled !== false;
          commands.push({
            id: `toggle:${k.id}:${p.name}`,
            category: k.label,
            label: `${enabled ? "Disable" : "Enable"} ${name}`,
            action: async () => {
              const action = enabled ? "disable" : "enable";
              await apiFetch(this.apiBase, `/plugins/${k.id}/${p.name}/${action}`, { method: "POST" });
              await this._registerGlobalCommands();
            },
          });
          if (k.id === "pipe" && enabled) {
            commands.push({
              id: `sync:${p.name}`,
              category: "Pipe",
              label: `Sync ${name}`,
              action: () => apiFetch(this.apiBase, `/sync/${p.name}`, { method: "POST" }),
            });
          }
        }
      }
      commands.push({
        id: "sync:all",
        category: "Pipe",
        label: "Sync All Pipes",
        action: () => apiFetch(this.apiBase, `/sync`, { method: "POST" }),
      });
      commands.push({
        id: "seed:transforms",
        category: "Transform",
        label: "Seed Default Transforms",
        action: () => apiFetch(this.apiBase, `/transforms/seed`, { method: "POST" }),
      });
    } catch { /* */ }
    this._registeredCommands.set("global", commands);
  }

  _buildCommands() {
    const commands = [];
    for (const cmds of this._registeredCommands.values()) {
      commands.push(...cmds);
    }
    this._paletteCommands = commands;
  }

  _executePaletteCommand(e) {
    const cmd = e.detail;
    if (cmd.path) {
      this._openTab(cmd.path, cmd.label);
    } else if (cmd.action) {
      cmd.action();
    }
    this._paletteOpen = false;
    this._navPaletteOpen = false;
  }

  _nextTabId = 1;

  _navigateTo(path, label) {
    if (this._tabs.length === 0 || !this._activeTabId) {
      this._openTab(path, label);
      return;
    }
    const lbl = label || this._labelForPath(path);
    this._tabs = this._tabs.map((t) =>
      t.id === this._activeTabId ? { ...t, path, label: lbl } : t,
    );
    this._router.goto(path);
    this._saveWorkspace();
  }

  _openTab(path, label) {
    const id = this._nextTabId++;
    this._tabs = [...this._tabs, { id, path, label: label || this._labelForPath(path) }];
    this._activeTabId = id;
    this._router.goto(path);
    this._saveWorkspace();
  }

  async _addTab() {
    await this._buildNavCommands();
    this._navPaletteOpen = true;
  }

  _closeTab(id) {
    const idx = this._tabs.findIndex((t) => t.id === id);
    if (idx === -1) return;
    const newTabs = this._tabs.filter((t) => t.id !== id);
    this._tabs = newTabs;
    if (this._activeTabId === id) {
      if (newTabs.length > 0) {
        const next = newTabs[Math.min(idx, newTabs.length - 1)];
        this._activeTabId = next.id;
        this._router.goto(next.path);
      } else {
        this._activeTabId = null;
        window.history.pushState({}, "", "/");
      }
    }
    this._saveWorkspace();
  }

  _switchTab(id) {
    const tab = this._tabs.find((t) => t.id === id);
    if (!tab) return;
    this._activeTabId = id;
    window.history.pushState({}, "", tab.path);
    this._router.goto(tab.path);
    this._saveWorkspace();
  }

  _saveWorkspaceTimer = null;

  _saveWorkspace() {
    clearTimeout(this._saveWorkspaceTimer);
    this._saveWorkspaceTimer = setTimeout(() => {
      const state = {
        tabs: this._tabs,
        activeTabId: this._activeTabId,
        nextTabId: this._nextTabId,
      };
      apiFetch(this.apiBase, `/workspace`, { method: "PUT", json: state }).catch(() => {});
    }, 300);
  }

  async _loadWorkspace() {
    try {
      const state = await apiFetch(this.apiBase, `/workspace`);
      if (!state) return;
      if (state.tabs && state.tabs.length > 0) {
        this._tabs = state.tabs;
        this._activeTabId = state.activeTabId || state.tabs[0].id;
        this._nextTabId = state.nextTabId || (Math.max(...state.tabs.map((t) => t.id)) + 1);
        // If URL has a specific path (shared link), open it
        const urlPath = window.location.pathname;
        if (urlPath && urlPath !== "/" && !this._tabs.some((t) => t.path === urlPath)) {
          this._openTab(urlPath);
          return;
        }
        // Navigate to the active tab
        const active = this._tabs.find((t) => t.id === this._activeTabId);
        if (active) this._router.goto(active.path);
      } else {
        // No saved state -- open from URL if present
        const path = window.location.pathname;
        if (path && path !== "/") this._openTab(path);
      }
    } catch {
      // No workspace -- open from URL
      const path = window.location.pathname;
      if (path && path !== "/") this._openTab(path);
    }
  }

  _labelForPath(path) {
    const p = path.replace(/^\/+/, "");
    if (!p || p === "settings") return "Data Flow";
    if (p === "settings/overview") return "Data Flow";
    const parts = p.split("/");
    if (parts[0] === "settings") {
      if (parts.length === 2) {
        const kind = PLUGIN_KINDS.find((k) => k.id === parts[1]);
        return kind ? kind.label : parts[1];
      }
      if (parts.length >= 3) return parts[2];
    }
    const comp = this._components.find((c) => c.name === parts[0]);
    return comp ? (comp.display_name || comp.name) : parts[0];
  }

  async _refreshComponents() {
    this._components = (await this._fetch("/components")) || [];
  }

  async _fetchData() {
    this._loading = true;
    try {
      const [components, dbStatus] = await Promise.all([
        this._fetch("/components"),
        this._fetch("/db/status"),
      ]);
      this._components = components || [];
      this._dbStatus = dbStatus;
    } catch (e) {
      console.error("Failed to fetch data:", e);
    }
    this._loading = false;
    this._registerGlobalCommands();
    await this._loadWorkspace();
  }

  async _fetch(path) {
    return apiFetch(this.apiBase, path);
  }

  _activeTab() {
    const path = window.location.pathname.replace(/^\/+/, "") || "";
    return path.split("/")[0] || (this._components.length > 0 ? this._components[0].name : "settings");
  }

  _startDrag(side) {
    return (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const startWidth = side === "left" ? this._leftWidth : this._rightWidth;
      const divider = e.target;
      divider.classList.add("dragging");

      const onMove = (ev) => {
        const delta = side === "left" ? ev.clientX - startX : startX - ev.clientX;
        const newWidth = Math.max(80, Math.min(400, startWidth + delta));
        if (side === "left") {
          this._leftWidth = newWidth;
        } else {
          this._rightWidth = newWidth;
        }
      };

      const onUp = () => {
        divider.classList.remove("dragging");
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };

      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    };
  }

  render() {
    if (this._loading) {
      return html`<shenas-page loading></shenas-page>`;
    }

    const active = this._activeTab();

    return html`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.png" alt="shenas" />
            <h1>shenas</h1>
          </div>
          <nav class="nav">
            ${this._components.map((c) => this._navItem(c.name, c.display_name || c.name, active))}
            ${this._navItem("settings", "Settings", active)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length > 0
            ? html`
              <div class="tab-bar">
                ${this._tabs.map((t) => html`
                  <div class="tab-item ${t.id === this._activeTabId ? "active" : ""}"
                    @click=${() => this._switchTab(t.id)}>
                    <span>${t.label}</span>
                    <button class="tab-close" @click=${(e) => { e.stopPropagation(); this._closeTab(t.id); }}>x</button>
                  </div>
                `)}
                <button class="tab-add" title="New tab" @click=${this._addTab}>+</button>
              </div>
              <div class="tab-content">
                ${this._router.outlet()}
              </div>`
            : html`
              <div class="empty-state">
                <img src="/static/images/shenas.png" alt="shenas" />
                <p>Open a page from the sidebar or press Ctrl+O</p>
              </div>`}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._inspectTable ? this._renderInspect() : this._renderDbStats()}
        </div>
      </div>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${this._executePaletteCommand}
        @close=${() => { this._paletteOpen = false; }}
      ></shenas-command-palette>
      <shenas-command-palette
        ?open=${this._navPaletteOpen}
        .commands=${this._navCommands}
        @execute=${this._executePaletteCommand}
        @close=${() => { this._navPaletteOpen = false; }}
      ></shenas-command-palette>
    `;
  }

  _navItem(id, label, active) {
    return html`
      <a class="nav-item" href="/${id}" aria-selected=${active === id}
        @click=${(e) => { e.preventDefault(); (e.ctrlKey || e.metaKey) ? this._openTab(`/${id}`, label) : this._navigateTo(`/${id}`, label); }}>
        ${label}
      </a>
    `;
  }

  _renderDynamicHome() {
    if (this._components.length > 0) {
      return this._renderDynamicTab(this._components[0].name);
    }
    return this._renderSettings("pipe");
  }

  _renderDynamicTab(tab) {
    const comp = this._components.find((c) => c.name === tab);
    if (!comp) return html`<p class="empty">Unknown page: ${tab}</p>`;
    if (!this._loadedScripts.has(comp.js)) {
      this._loadedScripts = new Set([...this._loadedScripts, comp.js]);
      const script = document.createElement("script");
      script.type = "module";
      script.src = comp.js;
      document.head.appendChild(script);
    }
    return html`<div class="component-host">
      ${this._getOrCreateElement(comp)}
    </div>`;
  }

  _renderPluginDetail(kind, name, tab = "details") {
    return html`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${kind}"
      name="${name}"
      active-tab="${tab}"
    ></shenas-plugin-detail>`;
  }

  _renderSettings(kind) {
    return html`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${kind || 'overview'}"
      .onNavigate=${(k) => {
        this._navigateTo(`/settings/${k}`);
      }}
    ></shenas-settings>`;
  }

  async _inspect(schema, table) {
    if (!/^[a-zA-Z_]\w*$/.test(schema) || !/^[a-zA-Z_]\w*$/.test(table)) return;
    const key = `${schema}.${table}`;
    if (this._inspectTable === key) {
      this._inspectTable = null;
      this._inspectRows = null;
      return;
    }
    this._inspectTable = key;
    this._inspectRows = null;
    try {
      this._inspectRows = (await apiFetch(this.apiBase, `/db/preview/${schema}/${table}?limit=50`)) || [];
    } catch {
      this._inspectRows = [];
    }
  }

  _renderDbStats() {
    const db = this._dbStatus;
    if (!db) return html`<p class="empty">No database</p>`;
    return html`
      <div class="db-section">
        <div class="db-meta">
          ${db.size_mb != null
            ? html`<code>${db.size_mb} MB</code>`
            : html`<span>Not created</span>`}
        </div>
        ${(db.schemas || []).map(
          (s) => html`
            <h4>${s.name}</h4>
            ${s.tables.map(
              (t) => html`
                <div class="db-table-row">
                  <span class="db-table-name">${t.name}</span>
                  <span class="db-table-count">${t.rows}</span>
                </div>
                ${t.earliest
                  ? html`<span class="db-date-range">${t.earliest} - ${t.latest}</span>`
                  : ""}
              `,
            )}
          `,
        )}
      </div>
    `;
  }

  _renderInspect() {
    return html`
      <div class="inspect-header">
        <h4>${this._inspectTable}</h4>
        <button class="inspect-close" title="Close" @click=${() => { this._inspectTable = null; this._inspectRows = null; }}>x</button>
      </div>
      ${!this._inspectRows
        ? html`<p class="loading" style="font-size:0.75rem">Loading...</p>`
        : this._inspectRows.length === 0
          ? html`<p class="empty" style="font-size:0.75rem">No rows</p>`
          : html`
            <div style="overflow-x: auto;">
              <table class="inspect-table">
                <thead>
                  <tr>${Object.keys(this._inspectRows[0]).map((c) => html`<th>${c}</th>`)}</tr>
                </thead>
                <tbody>
                  ${this._inspectRows.map(
                    (row) => html`<tr>${Object.keys(row).map((c) => html`<td title="${row[c] ?? ""}">${row[c] ?? ""}</td>`)}</tr>`,
                  )}
                </tbody>
              </table>
            </div>
          `}
    `;
  }

  _getOrCreateElement(comp) {
    if (!this._elementCache.has(comp.name)) {
      const el = document.createElement(comp.tag);
      el.setAttribute("api-base", this.apiBase);
      this._elementCache.set(comp.name, el);
    }
    return this._elementCache.get(comp.name);
  }
}

customElements.define("shenas-app", ShenasApp);
