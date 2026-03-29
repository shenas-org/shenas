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
    this._rightWidth = 160;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this.addEventListener("plugin-state-changed", () => this._refreshComponents());
  }

  async _refreshComponents() {
    this._components = (await this._fetch("/components")) || [];
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
            ${this._components.map((c) => this._navItem(c.name, c.name, active))}
            ${this._navItem("settings", "Settings", active)}
          </nav>
        </div>
        <div class="divider" @mousedown=${this._startDrag("left")}></div>
        <div class="panel-middle">
          ${this._router.outlet()}
        </div>
        <div class="divider" @mousedown=${this._startDrag("right")}></div>
        <div class="panel-right" style="width: ${this._rightWidth}px">
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
