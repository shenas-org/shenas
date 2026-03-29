import { LitElement, html, css } from "lit";
import { Router } from "@lit-labs/router";

class ShenasApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _pipes: { state: true },
    _dbStatus: { state: true },
    _components: { state: true },
    _loading: { state: true },
    _loadedScripts: { state: true },
  };

  _router = new Router(this, [
    { path: "/", render: () => this._renderDb() },
    { path: "/database", render: () => this._renderDb() },
    { path: "/pipes", render: () => this._renderPipes() },
    { path: "/settings", render: () => this._renderSettings("pipe") },
    {
      path: "/settings/:kind",
      render: ({ kind }) => this._renderSettings(kind),
    },
    { path: "/:tab", render: ({ tab }) => this._renderDynamicTab(tab) },
  ]);

  static styles = css`
    :host {
      display: block;
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1rem;
      color: #222;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 1.5rem;
    }
    .header img {
      width: 48px;
      height: 48px;
    }
    .header h1 {
      margin: 0;
      font-size: 1.5rem;
    }
    .tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid #e0e0e0;
      margin-bottom: 1.5rem;
    }
    .tab {
      padding: 0.6rem 1.2rem;
      cursor: pointer;
      border: none;
      background: none;
      font-size: 0.95rem;
      color: #666;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: color 0.15s, border-color 0.15s;
      text-decoration: none;
    }
    .tab:hover {
      color: #222;
    }
    .tab[aria-selected="true"] {
      color: #222;
      border-bottom-color: #0066cc;
      font-weight: 600;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .card {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1rem;
      background: #fff;
    }
    .card h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
    }
    .card .meta {
      color: #888;
      font-size: 0.85rem;
    }
    .card .desc {
      margin-top: 0.5rem;
      font-size: 0.85rem;
      color: #555;
    }
    .status {
      font-size: 0.9rem;
      color: #555;
    }
    .status code {
      background: #f0f0f0;
      padding: 2px 6px;
      border-radius: 3px;
    }
    .schema-row {
      display: flex;
      justify-content: space-between;
      padding: 0.3rem 0;
      border-bottom: 1px solid #f0f0f0;
    }
    .schema-row:last-child {
      border-bottom: none;
    }
    a {
      color: #0066cc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
    .empty {
      color: #888;
      padding: 1rem 0;
    }
    .component-host {
      margin-top: 1rem;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._pipes = [];
    this._dbStatus = null;
    this._components = [];
    this._loading = true;
    this._loadedScripts = new Set();
    this._elementCache = new Map();
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
  }

  async _fetchData() {
    this._loading = true;
    try {
      const [pipes, db, components] = await Promise.all([
        this._fetch("/plugins/pipe"),
        this._fetch("/db/status"),
        this._fetch("/components"),
      ]);
      this._pipes = pipes || [];
      this._dbStatus = db;
      this._components = components || [];
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
    const path = window.location.pathname.replace(/^\/+/, "") || "database";
    return path.split("/")[0];
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading...</p>`;
    }

    const active = this._activeTab();

    return html`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      <div class="tabs" role="tablist">
        ${this._tabLink("database", "Database", active)}
        ${this._tabLink("pipes", "Pipes", active)}
        ${this._components.map((c) => this._tabLink(c.name, c.name, active))}
        ${this._tabLink("settings", "Settings", active)}
      </div>

      ${this._router.outlet()}
    `;
  }

  _tabLink(id, label, active) {
    return html`
      <a
        class="tab"
        role="tab"
        href="/${id}"
        aria-selected=${active === id}
      >
        ${label}
      </a>
    `;
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

  _renderSettings(kind) {
    return html`<shenas-settings
      api-base="${this.apiBase}"
      active-kind="${kind || 'pipe'}"
      .onNavigate=${(k) => {
        this._router.goto(`/settings/${k}`);
      }}
    ></shenas-settings>`;
  }

  _getOrCreateElement(comp) {
    if (!this._elementCache.has(comp.name)) {
      const el = document.createElement(comp.tag);
      el.setAttribute("api-base", this.apiBase);
      this._elementCache.set(comp.name, el);
    }
    return this._elementCache.get(comp.name);
  }

  _renderDb() {
    const db = this._dbStatus;
    if (!db) return html`<p class="empty">No database info available</p>`;
    return html`
      <div class="status">
        <p>Path: <code>${db.db_path}</code></p>
        ${db.size_mb != null
          ? html`<p>Size: ${db.size_mb} MB</p>`
          : html`<p>Not created yet</p>`}
      </div>
      ${(db.schemas || []).map(
        (s) => html`
          <h3>${s.name}</h3>
          ${s.tables.map(
            (t) => html`
              <div class="schema-row">
                <span>${t.name}</span>
                <span class="meta">
                  ${t.rows} rows
                  ${t.earliest
                    ? html` &middot; ${t.earliest} - ${t.latest}`
                    : ""}
                </span>
              </div>
            `,
          )}
        `,
      )}
    `;
  }

  _renderPipes() {
    if (this._pipes.length === 0) {
      return html`<p class="empty">No pipes installed</p>`;
    }
    return html`
      <div class="cards">
        ${this._pipes.map(
          (p) => html`
            <div class="card">
              <h3>${p.name}</h3>
              <div class="meta">${p.version}</div>
              ${p.description
                ? html`<div class="desc">${p.description}</div>`
                : ""}
            </div>
          `,
        )}
      </div>
    `;
  }
}

customElements.define("shenas-app", ShenasApp);
