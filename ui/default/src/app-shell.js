import { LitElement, html, css } from "lit";
import { Router } from "@lit-labs/router";

class ShenasApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _components: { state: true },
    _loading: { state: true },
    _loadedScripts: { state: true },
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
      this._components = (await this._fetch("/components")) || [];
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
