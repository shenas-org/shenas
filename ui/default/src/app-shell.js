import { LitElement, html, css } from "lit";
import { Router } from "@lit-labs/router";
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
  };

  _router = new Router(this, [
    { path: "/", render: () => this._renderDynamicHome() },
    { path: "/settings", render: () => this._renderSettings("pipe") },
    {
      path: "/settings/:kind",
      render: ({ kind }) => this._renderSettings(kind),
    },
    {
      path: "/settings/:kind/:name",
      render: ({ kind, name }) => this._renderPluginDetail(kind, name),
    },
    {
      path: "/settings/:kind/:name/transforms",
      render: ({ kind, name }) => this._renderPluginDetail(kind, name, "transforms"),
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
        color: #222;
      }
      .layout {
        display: flex;
        height: 100%;
      }
      .panel-left {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-right: 1px solid #e0e0e0;
      }
      .panel-middle {
        flex: 1;
        min-width: 0;
        overflow-y: auto;
        padding: 1.5rem 2rem;
      }
      .panel-right {
        flex-shrink: 0;
        overflow-y: auto;
        padding: 1.5rem 1rem;
        border-left: 1px solid #e0e0e0;
      }
      .divider {
        width: 4px;
        cursor: col-resize;
        background: transparent;
        flex-shrink: 0;
      }
      .divider:hover,
      .divider.dragging {
        background: #d0d0d0;
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
        color: #666;
        text-decoration: none;
        border-radius: 4px;
        border: none;
        background: none;
        cursor: pointer;
        text-align: left;
      }
      .nav-item:hover {
        background: #f5f5f5;
        color: #222;
      }
      .nav-item[aria-selected="true"] {
        background: #f0f4ff;
        color: #222;
        font-weight: 600;
      }
      .component-host {
        margin-top: 1rem;
      }
      .db-section h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #888;
        letter-spacing: 0.05em;
        margin: 1rem 0 0.4rem;
      }
      .db-section h4:first-child {
        margin-top: 0;
      }
      .db-meta {
        font-size: 0.8rem;
        color: #666;
        margin: 0 0 0.8rem;
      }
      .db-meta code {
        background: #f0f0f0;
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 0.75rem;
      }
      .db-table-row {
        display: flex;
        justify-content: space-between;
        padding: 0.2rem 0;
        font-size: 0.8rem;
        border-bottom: 1px solid #f5f5f5;
      }
      .db-table-row:last-child {
        border-bottom: none;
      }
      .db-table-name {
        color: #333;
      }
      .db-table-count {
        color: #888;
        font-size: 0.75rem;
      }
      .db-date-range {
        font-size: 0.7rem;
        color: #aaa;
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
        color: #222;
        text-transform: none;
        letter-spacing: normal;
      }
      .inspect-close {
        background: none;
        border: none;
        cursor: pointer;
        color: #888;
        font-size: 1rem;
        padding: 0;
        line-height: 1;
      }
      .inspect-close:hover {
        color: #222;
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
        color: #666;
        font-weight: 500;
        border-bottom: 1px solid #e0e0e0;
        white-space: nowrap;
      }
      .inspect-table td {
        padding: 0.2rem 0.4rem;
        border-bottom: 1px solid #f5f5f5;
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
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this.addEventListener("plugin-state-changed", () => this._refreshComponents());
    this.addEventListener("inspect-table", (e) => this._inspect(e.detail.schema, e.detail.table));
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
  }

  async _fetch(path) {
    const resp = await fetch(`${this.apiBase}${path}`);
    if (!resp.ok) return null;
    return resp.json();
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
      return html`<p class="loading">Loading...</p>`;
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
          ${this._router.outlet()}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
          ${this._inspectTable ? this._renderInspect() : this._renderDbStats()}
        </div>
      </div>
    `;
  }

  _navItem(id, label, active) {
    return html`
      <a class="nav-item" href="/${id}" aria-selected=${active === id}>
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
      active-kind="${kind || 'pipe'}"
      .onNavigate=${(k) => {
        this._router.goto(`/settings/${k}`);
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
      const resp = await fetch(`${this.apiBase}/db/preview/${schema}/${table}?limit=50`);
      this._inspectRows = resp.ok ? await resp.json() : [];
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
