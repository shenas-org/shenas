import { LitElement, html, css } from "lit";
import { Router } from "@lit-labs/router";
import {
  arrowQuery,
  gql,
  gqlFull,
  PLUGIN_KINDS,
  matchesHotkey,
  openExternal,
  sortActions,
  linkStyles,
  utilityStyles,
} from "shenas-frontends";
import { SETTINGS_NAV_ITEMS } from "./settings-page.ts";

interface DashboardInfo {
  name: string;
  display_name?: string;
  tag: string;
  js: string;
}

interface PluginSummary {
  name: string;
  displayName?: string;
  enabled?: boolean;
  syncedAt?: string;
  hasAuth?: boolean;
  isAuthenticated?: boolean;
}

interface TabInfo {
  id: number;
  path: string;
  label: string;
}

interface Command {
  id: string;
  label: string;
  category?: string;
  description?: string;
  path?: string;
  action?: () => void;
}

interface DbStatus {
  size_mb?: number;
  schemas: Array<{
    name: string;
    tables: Array<{ name: string; rows: number; cols: number; earliest?: string; latest?: string }>;
  }>;
  [key: string]: unknown;
}

class ShenasApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _dashboards: { state: true },
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
    _settingsOpen: { state: true },
    _remoteUser: { state: true },
    _navCommands: { state: true },
    _tabs: { state: true },
    _activeTabId: { state: true },
    _allPlugins: { state: true },
    _rightOpen: { state: true },
    _mobileDrawerOpen: { state: true },
  };

  declare apiBase: string;
  declare _dashboards: DashboardInfo[];
  declare _loading: boolean;
  declare _loadedScripts: Set<string>;
  declare _leftWidth: number;
  declare _rightWidth: number;
  declare _dbStatus: DbStatus | null;
  declare _inspectTable: string | null;
  declare _inspectRows: Record<string, unknown>[] | null;
  declare _paletteOpen: boolean;
  declare _paletteCommands: Command[];
  declare _navPaletteOpen: boolean;
  declare _settingsOpen: boolean | undefined;
  declare _remoteUser: Record<string, unknown> | null;
  declare _navCommands: Command[];
  declare _tabs: TabInfo[];
  declare _activeTabId: number | null;
  declare _allPlugins: Record<string, PluginSummary[]>;
  declare _rightOpen: boolean;
  declare _mobileDrawerOpen: boolean;
  private _elementCache = new Map<string, HTMLElement>();
  private _registeredCommands = new Map<string, Command[]>();
  private _keyHandler: ((e: KeyboardEvent) => void) | null = null;
  private _schemaPlugins: Record<string, string[]> = {};
  private _deviceName = "";
  private _hotkeys: Record<string, string> = {};
  private _pluginDisplayNames: Record<string, string> = {};
  private _nextTabId = 1;
  private _saveWorkspaceTimer: ReturnType<typeof setTimeout> | null = null;

  _router = new Router(this, [
    { path: "/", render: () => this._renderDynamicHome() },
    { path: "/settings", render: () => this._renderSettings("flow") },
    {
      path: "/settings/:kind",
      render: (params: { [key: string]: string | undefined }) => this._renderSettings(params?.kind ?? ""),
    },
    {
      path: "/settings/:kind/:name",
      render: (params: { [key: string]: string | undefined }) =>
        this._renderPluginDetail(params?.kind ?? "", params?.name ?? ""),
    },
    {
      path: "/settings/:kind/:name/config",
      render: (params: { [key: string]: string | undefined }) =>
        this._renderPluginDetail(params?.kind ?? "", params?.name ?? "", "config"),
    },
    {
      path: "/settings/:kind/:name/auth",
      render: (params: { [key: string]: string | undefined }) =>
        this._renderPluginDetail(params?.kind ?? "", params?.name ?? "", "auth"),
    },
    {
      path: "/settings/:kind/:name/data",
      render: (params: { [key: string]: string | undefined }) =>
        this._renderPluginDetail(params?.kind ?? "", params?.name ?? "", "data"),
    },
    {
      path: "/settings/:kind/:name/logs",
      render: (params: { [key: string]: string | undefined }) =>
        this._renderPluginDetail(params?.kind ?? "", params?.name ?? "", "logs"),
    },
    { path: "/logs", render: () => html`<shenas-logs api-base="${this.apiBase}"></shenas-logs>` },
    {
      path: "/:tab",
      render: (params: { [key: string]: string | undefined }) => this._renderDynamicTab(params?.tab ?? ""),
    },
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
        box-sizing: border-box;
      }
      .panel-left {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
        display: flex;
        flex-direction: column;
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
        min-height: 0;
        position: relative;
      }
      .tab-content-inner {
        position: absolute;
        inset: 0;
        padding: 1.5rem 2rem;
        overflow-y: auto;
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
        width: 120px;
        height: 120px;
        border-radius: 12px;
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
      .settings-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0.8rem;
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .settings-toggle:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .chevron {
        transition: transform 0.15s;
        font-size: 1.1rem;
      }
      .chevron.open {
        transform: rotate(90deg);
      }
      .settings-sub {
        padding-left: 0.5rem;
      }
      .nav-sub-item {
        display: block;
        padding: 0.35rem 0.8rem;
        font-size: 0.82rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .nav-sub-item:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .nav-sub-item[aria-selected="true"] {
        background: var(--shenas-bg-selected, #f0f4ff);
        color: var(--shenas-text, #222);
        font-weight: 600;
      }
      .sub-heading {
        display: block;
        padding: 0.4rem 0.8rem 0.2rem;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--shenas-text-faint, #aaa);
      }
      .sidebar-footer {
        margin-top: auto;
        padding: 0.8rem;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
      }
      .auth-link {
        display: block;
        padding: 0.5rem 0.8rem;
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        text-decoration: none;
        border-radius: 4px;
      }
      .auth-link:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text, #222);
      }
      .device-name {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.2rem 0.8rem;
        font-size: 0.7rem;
        color: var(--shenas-text-faint, #aaa);
      }
      .device-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--shenas-text-faint, #ccc);
        flex-shrink: 0;
      }
      .device-dot.connected {
        background: var(--shenas-success, #2e7d32);
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
      .right-toggle {
        width: 14px;
        flex-shrink: 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: none;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.7rem;
        padding: 0;
      }
      .right-toggle:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
        color: var(--shenas-text-secondary, #666);
      }
      .panel-right.collapsed {
        display: none;
      }
      .drawer-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.3);
        z-index: 200;
      }
      /* Bottom nav for mobile */
      .bottom-nav {
        display: none;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
        background: var(--shenas-bg, #fff);
        padding: 0.3rem 0;
      }
      .bottom-nav nav {
        display: flex;
        justify-content: space-around;
      }
      .bottom-nav .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        font-size: 0.6rem;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        color: var(--shenas-text-muted, #888);
        text-decoration: none;
      }
      .bottom-nav .nav-item[aria-selected="true"] {
        color: var(--shenas-accent, #0066cc);
      }
      .bottom-nav .nav-item svg {
        flex-shrink: 0;
      }
      /* Responsive: narrow screens */
      @media (max-width: 768px) {
        .layout {
          flex-direction: column;
          padding-top: env(safe-area-inset-top, 0);
          padding-left: env(safe-area-inset-left, 0);
          padding-right: env(safe-area-inset-right, 0);
        }
        .bottom-nav {
          padding-bottom: calc(0.3rem + env(safe-area-inset-bottom, 0));
        }
        .panel-left {
          display: none;
        }
        .panel-right {
          display: none;
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          width: 260px;
          z-index: 201;
          background: var(--shenas-bg, #fff);
          box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
          transform: translateX(100%);
          transition: transform 0.2s ease;
        }
        .panel-right.mobile-open {
          display: block;
          transform: translateX(0);
        }
        .drawer-overlay.visible {
          display: block;
        }
        .divider {
          display: none;
        }
        .right-toggle {
          display: none;
        }
        .panel-middle {
          flex: 1;
        }
        .tab-bar {
          display: none;
        }
        .tab-content-inner {
          padding: 1rem;
        }
        .bottom-nav {
          display: block;
        }
        .header {
          display: none;
        }
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this._dashboards = [];
    this._loading = true;
    this._loadedScripts = new Set();
    this._leftWidth = 160;
    this._rightWidth = 220;
    this._dbStatus = null;
    this._inspectTable = null;
    this._inspectRows = null;
    this._paletteOpen = false;
    this._paletteCommands = [];
    this._navPaletteOpen = false;
    this._navCommands = [];
    this._tabs = [];
    this._activeTabId = null;
    this._allPlugins = {};
    this._rightOpen = true;
    this._mobileDrawerOpen = false;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchData();
    this.addEventListener("plugin-state-changed", () => this._refreshDashboards());
    this.addEventListener("job-start", ((e: CustomEvent) =>
      this._getJobPanel()?.addJob(e.detail.id, e.detail.label)) as EventListener);
    this.addEventListener("job-log", ((e: CustomEvent) =>
      this._getJobPanel()?.appendLine(e.detail.id, e.detail.text)) as EventListener);
    this.addEventListener("job-finish", ((e: CustomEvent) =>
      this._getJobPanel()?.finishJob(e.detail.id, e.detail.ok, e.detail.message)) as EventListener);
    this.addEventListener("inspect-table", ((e: CustomEvent) =>
      this._inspect(e.detail.schema, e.detail.table)) as unknown as EventListener);
    this.addEventListener("page-title", ((e: CustomEvent) => {
      if (this._activeTabId != null) {
        this._tabs = this._tabs.map((t) => (t.id === this._activeTabId ? { ...t, label: e.detail.title } : t));
      }
    }) as EventListener);
    this.addEventListener("navigate", ((e: CustomEvent) =>
      this._navigateTo(e.detail.path, e.detail.label)) as EventListener);
    this.addEventListener("register-command", ((e: CustomEvent) => {
      const { componentId, commands } = e.detail as { componentId: string; commands: Command[] };
      if (!commands || commands.length === 0) {
        this._registeredCommands.delete(componentId);
      } else {
        this._registeredCommands.set(componentId, commands);
      }
    }) as EventListener);
    this._keyHandler = (e: KeyboardEvent) => {
      for (const [actionId, binding] of Object.entries(this._hotkeys)) {
        if (binding && matchesHotkey(e, binding)) {
          for (const cmds of this._registeredCommands.values()) {
            const cmd = cmds.find((c) => c.id === actionId);
            if (cmd && cmd.action) {
              e.preventDefault();
              cmd.action();
              return;
            }
          }
        }
      }
    };
    document.addEventListener("keydown", this._keyHandler);
    this.addEventListener("hotkeys-changed", () => this._loadHotkeys());
    this.addEventListener("plugins-changed", ((e: CustomEvent) => {
      if (e.detail) this._allPlugins = e.detail;
      else this._allPlugins = {};
    }) as EventListener);
    // Touch swipe handlers for mobile drawer
    let _touchStartX = 0;
    let _touchStartY = 0;
    this.addEventListener(
      "touchstart",
      ((e: TouchEvent) => {
        _touchStartX = e.touches[0].clientX;
        _touchStartY = e.touches[0].clientY;
      }) as EventListener,
      { passive: true },
    );
    this.addEventListener(
      "touchend",
      ((e: TouchEvent) => {
        const dx = e.changedTouches[0].clientX - _touchStartX;
        const dy = e.changedTouches[0].clientY - _touchStartY;
        if (Math.abs(dy) > Math.abs(dx)) return;
        // Swipe left from right edge to open
        if (dx < -50 && _touchStartX > window.innerWidth - 40) {
          this._mobileDrawerOpen = true;
        }
        // Swipe right to close
        if (dx > 50 && this._mobileDrawerOpen) {
          this._mobileDrawerOpen = false;
        }
      }) as EventListener,
      { passive: true },
    );
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._keyHandler) {
      document.removeEventListener("keydown", this._keyHandler);
    }
  }

  async _loadHotkeys(): Promise<void> {
    const data = await gql(this.apiBase, `{ hotkeys }`);
    this._hotkeys = (data?.hotkeys as Record<string, string>) || {};
  }

  _togglePalette(): void {
    if (this._paletteOpen) {
      this._paletteOpen = false;
      return;
    }
    this._navPaletteOpen = false;
    this._buildCommands();
    this._paletteOpen = true;
  }

  async _toggleNavPalette(): Promise<void> {
    if (this._navPaletteOpen) {
      this._navPaletteOpen = false;
      return;
    }
    this._paletteOpen = false;
    await this._buildNavCommands();
    this._navPaletteOpen = true;
  }

  async _buildNavCommands(): Promise<void> {
    const commands: Command[] = [];

    // Components (top-level tabs)
    for (const c of this._dashboards) {
      commands.push({ id: `nav:${c.name}`, category: "Page", label: c.display_name || c.name, path: `/${c.name}` });
    }

    // Settings sections from shared PLUGIN_KINDS
    commands.push({ id: "nav:dataflow", category: "Settings", label: "Flow", path: "/settings/flow" });
    for (const k of PLUGIN_KINDS) {
      commands.push({ id: `nav:settings:${k.id}`, category: "Settings", label: k.label, path: `/settings/${k.id}` });
    }

    // Use cached plugin data for detail page navigation
    const allPlugins = PLUGIN_KINDS.flatMap((k) =>
      (this._allPlugins[k.id] || []).map((p) => ({ ...p, kind: k.id, kindLabel: k.label })),
    );

    for (const p of allPlugins) {
      commands.push({
        id: `nav:${p.kind}:${p.name}`,
        category: p.kindLabel,
        label: p.displayName || p.name,
        path: `/settings/${p.kind}/${p.name}`,
      });
    }

    this._navCommands = commands;
  }

  async _registerGlobalCommands(): Promise<void> {
    const commands: Command[] = [];
    const names: Record<string, string> = {};
    try {
      const schemaOwnership = this._schemaPlugins || {};

      for (const k of PLUGIN_KINDS) {
        const plugins = this._allPlugins[k.id] || [];
        for (const p of plugins) {
          const name = p.displayName || p.name;
          names[`${k.id}:${p.name}`] = name;
          const enabled = p.enabled !== false;
          commands.push({
            id: `toggle:${k.id}:${p.name}`,
            category: k.label,
            label: `Toggle ${name}`,
            action: async () => {
              const mutation = enabled
                ? `mutation($k: String!, $n: String!) { disablePlugin(kind: $k, name: $n) { ok } }`
                : `mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }`;
              await gqlFull(this.apiBase, mutation, { k: k.id, n: p.name });
              if (k.id === "ui" && !enabled) {
                window.location.replace(window.location.pathname + "?_switch=" + Date.now());
                return;
              }
              await this._fetchData();
            },
          });
          if (k.id === "ui") {
            commands.push({
              id: `switch-ui:${p.name}`,
              category: "Switch UI",
              label: `${name}${enabled ? " (active)" : ""}`,
              action: async () => {
                if (enabled) return;
                await gqlFull(
                  this.apiBase,
                  `mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }`,
                  { k: "ui", n: p.name },
                );
                window.location.replace(window.location.pathname + "?_switch=" + Date.now());
              },
            });
          }
          if (k.id === "source" && enabled) {
            commands.push({
              id: `sync:${p.name}`,
              category: "Pipe",
              label: `Sync ${name}`,
              action: () => {
                fetch(`${this.apiBase}/sync/${p.name}`, { method: "POST" });
              },
            });
            commands.push({
              id: `transform:pipe:${p.name}`,
              category: "Transform",
              label: `Run Transforms: ${name}`,
              action: () => {
                gqlFull(this.apiBase, `mutation($pipe: String!) { runPipeTransforms(pipe: $pipe) }`, { pipe: p.name });
              },
            });
          }
        }
      }
      commands.push({
        id: "sync:all",
        category: "Pipe",
        label: "Sync All Pipes",
        action: () => {
          fetch(`${this.apiBase}/sync`, { method: "POST" });
        },
      });
      commands.push({
        id: "seed:transforms",
        category: "Transform",
        label: "Seed Default Transforms",
        action: () => {
          gqlFull(this.apiBase, `mutation { seedTransforms }`);
        },
      });
      // Per-schema transform commands
      for (const s of this._allPlugins.schema || []) {
        const schemaTables = schemaOwnership[s.name] || [];
        for (const table of schemaTables) {
          commands.push({
            id: `transform:schema:${table}`,
            category: "Transform",
            label: `Run Transforms -> ${s.displayName || s.name}: ${table}`,
            action: () => {
              gqlFull(this.apiBase, `mutation($schema: String!) { runSchemaTransforms(schema: $schema) }`, {
                schema: table,
              });
            },
          });
        }
      }
    } catch {
      /* */
    }
    this._pluginDisplayNames = names;
    // System actions (also triggerable from Ctrl+P)
    commands.push(
      { id: "command-palette", category: "System", label: "Command Palette", action: () => this._togglePalette() },
      {
        id: "navigation-palette",
        category: "System",
        label: "Navigation Palette",
        action: () => this._toggleNavPalette(),
      },
      {
        id: "close-tab",
        category: "System",
        label: "Close Tab",
        action: () => {
          if (this._activeTabId != null) this._closeTab(this._activeTabId);
        },
      },
      { id: "new-tab", category: "System", label: "New Tab", action: () => this._addTab() },
    );
    this._registeredCommands.set("global", commands);
  }

  _buildCommands(): void {
    const commands: Command[] = [];
    for (const cmds of this._registeredCommands.values()) {
      commands.push(...cmds);
    }
    this._paletteCommands = sortActions(commands, this._hotkeys) as Command[];
  }

  _executePaletteCommand(e: CustomEvent): void {
    const cmd = e.detail as Command;
    if (cmd.path) {
      this._openTab(cmd.path, cmd.label);
    } else if (cmd.action) {
      cmd.action();
    }
    this._paletteOpen = false;
    this._navPaletteOpen = false;
  }

  _navigateTo(path: string, label?: string): void {
    if (this._tabs.length === 0 || !this._activeTabId) {
      this._openTab(path, label);
      return;
    }
    const lbl = label || this._labelForPath(path);
    this._tabs = this._tabs.map((t) => (t.id === this._activeTabId ? { ...t, path, label: lbl } : t));
    window.history.pushState({}, "", path);
    this._router.goto(path);
    this._saveWorkspace();
  }

  _openTab(path: string, label?: string): void {
    const id = this._nextTabId++;
    this._tabs = [...this._tabs, { id, path, label: label || this._labelForPath(path) }];
    this._activeTabId = id;
    window.history.pushState({}, "", path);
    this._router.goto(path);
    this._saveWorkspace();
  }

  async _addTab(): Promise<void> {
    await this._buildNavCommands();
    this._navPaletteOpen = true;
  }

  _closeTab(id: number): void {
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

  _switchTab(id: number): void {
    const tab = this._tabs.find((t) => t.id === id);
    if (!tab) return;
    this._activeTabId = id;
    window.history.pushState({}, "", tab.path);
    this._router.goto(tab.path);
    this._saveWorkspace();
  }

  _saveWorkspace(): void {
    if (this._saveWorkspaceTimer) clearTimeout(this._saveWorkspaceTimer);
    this._saveWorkspaceTimer = setTimeout(() => {
      const state = {
        tabs: this._tabs,
        activeTabId: this._activeTabId,
        nextTabId: this._nextTabId,
        rightPanelOpen: this._rightOpen,
      };
      gqlFull(this.apiBase, `mutation($data: JSON!) { saveWorkspace(data: $data) { ok } }`, { data: state }).catch(
        () => {},
      );
    }, 300);
  }

  async _loadWorkspace(): Promise<void> {
    try {
      const data = await gql(this.apiBase, `{ workspace }`);
      const state = data?.workspace as Record<string, unknown> | undefined;
      if (!state) return;
      if (state.tabs && (state.tabs as TabInfo[]).length > 0) {
        this._tabs = state.tabs as TabInfo[];
        this._activeTabId = (state.activeTabId as number) || (state.tabs as TabInfo[])[0].id;
        this._nextTabId = (state.nextTabId as number) || Math.max(...(state.tabs as TabInfo[]).map((t) => t.id)) + 1;
        // If URL has a specific path (shared link), open it
        const urlPath = window.location.pathname.replace(/\/+$/, "") || "/";
        if (urlPath && urlPath !== "/" && !this._tabs.some((t) => t.path === urlPath)) {
          this._openTab(urlPath);
          return;
        }
        // Navigate to the active tab
        const active = this._tabs.find((t) => t.id === this._activeTabId);
        if (active) this._router.goto(active.path);
      } else {
        // No saved state -- open from URL if present
        const path = window.location.pathname.replace(/\/+$/, "") || "/";
        if (path && path !== "/") this._openTab(path);
      }
    } catch {
      // No workspace -- open from URL
      const path = window.location.pathname;
      if (path && path !== "/") this._openTab(path);
    }
  }

  _labelForPath(path: string): string {
    const p = path.replace(/^\/+/, "");
    if (!p || p === "settings") return "Flow";
    if (p === "settings/flow") return "Flow";
    const parts = p.split("/");
    if (parts[0] === "settings") {
      if (parts.length === 2) {
        const kind = PLUGIN_KINDS.find((k) => k.id === parts[1]);
        return kind ? kind.label : parts[1];
      }
      if (parts.length >= 3) {
        const key = `${parts[1]}:${parts[2]}`;
        return this._pluginDisplayNames[key] || parts[2];
      }
    }
    const comp = this._dashboards.find((c) => c.name === parts[0]);
    return comp ? comp.display_name || comp.name : parts[0];
  }

  async _refreshDashboards(): Promise<void> {
    const data = await gql(this.apiBase, `{ dashboards }`);
    this._dashboards = (data?.dashboards as DashboardInfo[]) || [];
  }

  async _refreshPlugins(): Promise<void> {
    const data = await gql(
      this.apiBase,
      `{
      sources: plugins(kind: "source") { name displayName enabled syncedAt hasAuth isAuthenticated }
      datasets: plugins(kind: "dataset") { name displayName enabled }
      dashboardPlugins: plugins(kind: "dashboard") { name displayName enabled }
      frontends: plugins(kind: "frontend") { name displayName enabled }
      themes: plugins(kind: "theme") { name displayName enabled }
      models: plugins(kind: "model") { name displayName enabled }
    }`,
    );
    if (data) {
      this._allPlugins = {
        source: (data.sources as PluginSummary[]) || [],
        dataset: (data.datasets as PluginSummary[]) || [],
        dashboard: (data.dashboardPlugins as PluginSummary[]) || [],
        frontend: (data.frontends as PluginSummary[]) || [],
        theme: (data.themes as PluginSummary[]) || [],
        model: (data.models as PluginSummary[]) || [],
      };
    }
  }

  async _fetchData(): Promise<void> {
    this._loading = true;
    try {
      const data = await gql(
        this.apiBase,
        `{
        dashboards
        hotkeys
        workspace
        dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } }
        sources: plugins(kind: "source") { name displayName enabled syncedAt hasAuth isAuthenticated }
        datasets: plugins(kind: "dataset") { name displayName enabled }
        dashboardPlugins: plugins(kind: "dashboard") { name displayName enabled }
        frontends: plugins(kind: "frontend") { name displayName enabled }
        themes: plugins(kind: "theme") { name displayName enabled }
        models: plugins(kind: "model") { name displayName enabled }
        theme { css }
        deviceName
        schemaPlugins
      }`,
      );
      this._dashboards = (data?.dashboards as DashboardInfo[]) || [];
      this._dbStatus = data?.dbStatus as DbStatus | null;
      this._deviceName = (data?.deviceName as string) || "";
      this._hotkeys = (data?.hotkeys as Record<string, string>) || {};
      this._allPlugins = {
        source: (data?.sources as PluginSummary[]) || [],
        dataset: (data?.datasets as PluginSummary[]) || [],
        dashboard: (data?.dashboardPlugins as PluginSummary[]) || [],
        frontend: (data?.frontends as PluginSummary[]) || [],
        theme: (data?.themes as PluginSummary[]) || [],
        model: (data?.models as PluginSummary[]) || [],
      };
      this._schemaPlugins = (data?.schemaPlugins as Record<string, string[]>) || {};
      // Apply theme if not already injected by the server
      const themeData = data?.theme as Record<string, string> | undefined;
      if (themeData?.css && !document.querySelector("link[data-shenas-theme]")) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.setAttribute("data-shenas-theme", "");
        link.href = themeData.css;
        document.head.appendChild(link);
      }
      // Restore workspace
      const ws = data?.workspace as Record<string, unknown> | undefined;
      if (ws?.rightPanelOpen !== undefined) this._rightOpen = ws.rightPanelOpen as boolean;
      if (ws?.tabs && (ws.tabs as TabInfo[]).length > 0) {
        this._tabs = ws.tabs as TabInfo[];
        this._activeTabId = (ws.activeTabId as number) || (ws.tabs as TabInfo[])[0].id;
        this._nextTabId = (ws.nextTabId as number) || Math.max(...(ws.tabs as TabInfo[]).map((t) => t.id)) + 1;
        const urlPath = window.location.pathname.replace(/\/+$/, "") || "/";
        if (urlPath && urlPath !== "/" && !this._tabs.some((t) => t.path === urlPath)) {
          this._openTab(urlPath);
        } else {
          const active = this._tabs.find((t) => t.id === this._activeTabId);
          if (active) this._router.goto(active.path);
        }
      } else {
        const path = window.location.pathname.replace(/\/+$/, "") || "/";
        if (path && path !== "/") this._openTab(path);
      }
    } catch (e) {
      console.error("Failed to fetch data:", e);
    }
    this._loading = false;
    this._registerGlobalCommands();
    fetch(`${this.apiBase}/auth/me`)
      .then((r) => r.json())
      .then((d: Record<string, unknown>) => {
        this._remoteUser = (d.user as Record<string, unknown>) || null;
      })
      .catch(() => {
        this._remoteUser = null;
      });
  }

  _activeTab(): string {
    const active = this._tabs.find((t) => t.id === this._activeTabId);
    return (
      active?.path?.replace(/^\/+/, "")?.split("/")[0] ||
      (this._dashboards.length > 0 ? this._dashboards[0].name : "settings")
    );
  }

  _activePath(): string {
    const active = this._tabs.find((t) => t.id === this._activeTabId);
    return active?.path || window.location.pathname;
  }

  _startDrag(side: "left" | "right"): (e: MouseEvent) => void {
    return (e: MouseEvent) => {
      e.preventDefault();
      const startX = e.clientX;
      const startWidth = side === "left" ? this._leftWidth : this._rightWidth;
      const divider = e.target as HTMLElement;
      divider.classList.add("dragging");

      const onMove = (ev: MouseEvent) => {
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
      return html`<div
        style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--shenas-text-muted,#888);background:var(--shenas-bg,#f5f1eb)"
      >
        Loading...
      </div>`;
    }

    const active = this._activeTab();
    const activePath = this._activePath();
    // Auto-expand settings on first navigation to a settings route
    if (activePath.startsWith("/settings") && this._settingsOpen === undefined) this._settingsOpen = true;

    return html`
      <div class="layout">
        <div class="panel-left" style="width: ${this._leftWidth}px">
          <div class="header">
            <img src="/static/images/shenas.svg" alt="shenas" />
          </div>
          <nav class="nav">
            ${this._dashboards.map((c) => this._navItem(c.name, c.display_name || c.name, active))}
            ${this._navItem("logs", "Logs", active)}
            <a
              class="nav-link settings-toggle"
              @click=${() => {
                this._settingsOpen = !this._settingsOpen;
              }}
            >
              Settings
              <span class="chevron ${this._settingsOpen ? "open" : ""}">&rsaquo;</span>
            </a>
            ${this._settingsOpen
              ? html`
                  <div class="settings-sub">
                    ${SETTINGS_NAV_ITEMS.map((item) => this._settingsNavItem(item.id, item.label, activePath))}
                    <span class="sub-heading">Plugins</span>
                    ${PLUGIN_KINDS.map(
                      ({ id, label }) => html`
                        ${this._settingsNavItem(id, `${label} (${(this._allPlugins[id] || []).length})`, activePath)}
                      `,
                    )}
                  </div>
                `
              : ""}
          </nav>
          <div class="sidebar-footer">
            <a
              class="auth-link"
              href=${this._remoteUser ? "https://shenas.net/dashboard" : "/api/auth/login"}
              @click=${(e: MouseEvent) => {
                e.preventDefault();
                if (this._remoteUser) {
                  openExternal("https://shenas.net/dashboard");
                } else {
                  window.location.href = "/api/auth/login";
                }
              }}
            >
              ${this._remoteUser ? (this._remoteUser.name as string) || (this._remoteUser.email as string) : "Sign in"}
            </a>
            ${this._deviceName
              ? html`<span class="device-name"
                  ><span class="device-dot ${this._remoteUser ? "connected" : ""}"></span>${this._deviceName}</span
                >`
              : ""}
          </div>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._tabs.length > 0
            ? html` <div class="tab-bar">
                  ${this._tabs.map(
                    (t) => html`
                      <div
                        class="tab-item ${t.id === this._activeTabId ? "active" : ""}"
                        @click=${() => this._switchTab(t.id)}
                      >
                        <span>${t.label}</span>
                        <button
                          class="tab-close"
                          @click=${(e: MouseEvent) => {
                            e.stopPropagation();
                            this._closeTab(t.id);
                          }}
                        >
                          x
                        </button>
                      </div>
                    `,
                  )}
                  <button class="tab-add" title="New tab" @click=${this._addTab}>+</button>
                </div>
                <div class="tab-content">
                  <div class="tab-content-inner">${this._router.outlet()}</div>
                </div>`
            : html` <div class="empty-state">
                <img src="/static/images/shenas.svg" alt="shenas" />
                <p>Open a page from the sidebar</p>
              </div>`}
          <shenas-job-panel></shenas-job-panel>
        </div>
        <button
          class="right-toggle"
          @click=${() => {
            this._rightOpen = !this._rightOpen;
            this._saveWorkspace();
          }}
          title="${this._rightOpen ? "Collapse" : "Expand"} panel"
        >
          ${this._rightOpen ? "\u203a" : "\u2039"}
        </button>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div
          class="drawer-overlay ${this._mobileDrawerOpen ? "visible" : ""}"
          @click=${() => {
            this._mobileDrawerOpen = false;
          }}
        ></div>
        <div
          class="panel-right ${this._rightOpen ? "" : "collapsed"} ${this._mobileDrawerOpen ? "mobile-open" : ""}"
          style="width: ${this._rightWidth}px"
        >
          ${this._inspectTable ? this._renderInspect() : this._renderDbStats()}
        </div>
        <div class="bottom-nav">
          <nav>
            ${this._dashboards.map(
              (c) => html`
                <a
                  class="nav-item"
                  href="/${c.name}"
                  @click=${(e: MouseEvent) => {
                    e.preventDefault();
                    this._navigateTo(`/${c.name}`);
                  }}
                  aria-selected=${active === c.name}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 9h18M9 21V9" />
                  </svg>
                  <span>${c.display_name || c.name}</span>
                </a>
              `,
            )}
            <a
              class="nav-item"
              href="/logs"
              @click=${(e: MouseEvent) => {
                e.preventDefault();
                this._navigateTo("/logs");
              }}
              aria-selected=${active === "logs"}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
              <span>Logs</span>
            </a>
            <a
              class="nav-item"
              href="/settings"
              aria-selected=${activePath.startsWith("/settings")}
              @click=${(e: MouseEvent) => {
                e.preventDefault();
                this._navigateTo("/settings");
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3" />
                <path
                  d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"
                />
              </svg>
              <span>Settings</span>
            </a>
          </nav>
        </div>
      </div>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${this._executePaletteCommand}
        @close=${() => {
          this._paletteOpen = false;
        }}
      ></shenas-command-palette>
      <shenas-command-palette
        ?open=${this._navPaletteOpen}
        .commands=${this._navCommands}
        @execute=${this._executePaletteCommand}
        @close=${() => {
          this._navPaletteOpen = false;
        }}
      ></shenas-command-palette>
    `;
  }

  _navItem(id: string, label: string, active: string) {
    return html`
      <a
        class="nav-item"
        href="/${id}"
        aria-selected=${active === id}
        @click=${(e: MouseEvent) => {
          e.preventDefault();
          if (e.ctrlKey || e.metaKey) {
            this._openTab(`/${id}`, label);
          } else {
            this._navigateTo(`/${id}`, label);
          }
        }}
      >
        ${label}
      </a>
    `;
  }

  _settingsNavItem(id: string, label: string, activePath: string) {
    const path = `/settings/${id}`;
    const isActive = activePath === path || activePath.startsWith(path + "/");
    return html`
      <a
        class="nav-sub-item"
        href="${path}"
        aria-selected=${isActive}
        @click=${(e: MouseEvent) => {
          e.preventDefault();
          if (e.ctrlKey || e.metaKey) {
            this._openTab(path, label);
          } else {
            this._navigateTo(path, label);
          }
        }}
      >
        ${label}
      </a>
    `;
  }

  _renderDynamicHome() {
    if (this._dashboards.length > 0) {
      return this._renderDynamicTab(this._dashboards[0].name);
    }
    return this._renderSettings("source");
  }

  _renderDynamicTab(tab: string) {
    const comp = this._dashboards.find((c) => c.name === tab);
    if (!comp) return html`<p class="empty">Unknown page: ${tab}</p>`;
    if (!this._loadedScripts.has(comp.js)) {
      this._loadedScripts = new Set([...this._loadedScripts, comp.js]);
      const script = document.createElement("script");
      script.type = "module";
      script.src = comp.js;
      document.head.appendChild(script);
    }
    return html`<div class="component-host">${this._getOrCreateElement(comp)}</div>`;
  }

  _renderPluginDetail(kind: string, name: string, tab = "details") {
    const cached = (this._allPlugins[kind] || []).find((p) => p.name === name);
    return html`<shenas-plugin-detail
      api-base="${this.apiBase}"
      kind="${kind}"
      name="${name}"
      active-tab="${tab}"
      .dbStatus=${this._dbStatus}
      .schemaPlugins=${this._schemaPlugins}
      .initialInfo=${cached || null}
    ></shenas-plugin-detail>`;
  }

  _getAllActions(): Command[] {
    const seen = new Set<string>();
    const actions: Command[] = [];
    for (const cmds of this._registeredCommands.values()) {
      for (const cmd of cmds) {
        if (!seen.has(cmd.id) && cmd.action) {
          seen.add(cmd.id);
          actions.push({ id: cmd.id, label: cmd.label, category: cmd.category });
        }
      }
    }
    return sortActions(actions, this._hotkeys) as Command[];
  }

  _getJobPanel():
    | (HTMLElement & {
        addJob: (id: string, label: string) => void;
        appendLine: (id: string, text: string) => void;
        finishJob: (id: string, ok: boolean, message: string) => void;
      })
    | null {
    return this.shadowRoot?.querySelector("shenas-job-panel") as
      | (HTMLElement & {
          addJob: (id: string, label: string) => void;
          appendLine: (id: string, text: string) => void;
          finishJob: (id: string, ok: boolean, message: string) => void;
        })
      | null;
  }

  _renderSettings(kind: string) {
    return html`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${kind || "flow"}"
      .allActions=${this._getAllActions()}
      .allPlugins=${this._allPlugins}
      .schemaPlugins=${this._schemaPlugins}
      .remoteUser=${this._remoteUser}
      device-name=${this._deviceName || ""}
      .onNavigate=${(k: string) => {
        this._navigateTo(`/settings/${k}`);
      }}
      .onPluginsChanged=${(data: Record<string, PluginSummary[]>) => {
        this._allPlugins = data;
      }}
    ></shenas-settings>`;
  }

  async _inspect(schema: string, table: string): Promise<void> {
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
      this._inspectRows =
        ((await arrowQuery(this.apiBase, `SELECT * FROM "${schema}"."${table}" ORDER BY 1 DESC LIMIT 50`)) as Record<
          string,
          unknown
        >[]) || [];
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
          ${db.size_mb != null ? html`<code>${db.size_mb} MB</code>` : html`<span>Not created</span>`}
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
                ${t.earliest ? html`<span class="db-date-range">${t.earliest} - ${t.latest}</span>` : ""}
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
        <button
          class="inspect-close"
          title="Close"
          @click=${() => {
            this._inspectTable = null;
            this._inspectRows = null;
          }}
        >
          x
        </button>
      </div>
      ${!this._inspectRows
        ? html`<p class="loading" style="font-size:0.75rem">Loading...</p>`
        : this._inspectRows.length === 0
          ? html`<p class="empty" style="font-size:0.75rem">No rows</p>`
          : html`
              <div style="overflow-x: auto;">
                <table class="inspect-table">
                  <thead>
                    <tr>
                      ${Object.keys(this._inspectRows[0]).map((c) => html`<th>${c}</th>`)}
                    </tr>
                  </thead>
                  <tbody>
                    ${this._inspectRows.map(
                      (row) =>
                        html`<tr>
                          ${Object.keys(row).map((c) => html`<td title="${row[c] ?? ""}">${row[c] ?? ""}</td>`)}
                        </tr>`,
                    )}
                  </tbody>
                </table>
              </div>
            `}
    `;
  }

  _getOrCreateElement(comp: DashboardInfo): HTMLElement {
    if (!this._elementCache.has(comp.name)) {
      const el = document.createElement(comp.tag);
      el.setAttribute("api-base", this.apiBase);
      this._elementCache.set(comp.name, el);
    }
    return this._elementCache.get(comp.name)!;
  }
}

customElements.define("shenas-app", ShenasApp);
