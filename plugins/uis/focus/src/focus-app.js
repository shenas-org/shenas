import { LitElement, html, css } from "lit";

class FocusApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _components: { state: true },
    _activeIndex: { state: true },
    _loading: { state: true },
    _loadedScripts: { state: true },
    _hotkeys: { state: true },
    _paletteOpen: { state: true },
    _paletteCommands: { state: true },
    _uis: { state: true },
  };

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100vh;
      background: var(--shenas-bg, #f5f1eb);
      color: var(--shenas-text, #222);
    }
    .content {
      flex: 1;
      overflow: auto;
      position: relative;
    }
    .component-host {
      width: 100%;
      height: 100%;
    }
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--shenas-text-muted, #888);
    }
    .empty {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--shenas-text-muted, #888);
      flex-direction: column;
      gap: 0.5rem;
    }
    .bottom-nav {
      display: flex;
      justify-content: space-around;
      border-top: 1px solid var(--shenas-border, #e0e0e0);
      background: var(--shenas-bg, #fff);
      padding: 0.4rem 0;
      flex-shrink: 0;
    }
    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      font-size: 0.65rem;
      padding: 0.3rem 0.8rem;
      border-radius: 6px;
      color: var(--shenas-text-muted, #888);
      text-decoration: none;
      cursor: pointer;
      background: none;
      border: none;
      transition: color 0.15s;
    }
    .nav-item:hover {
      color: var(--shenas-text-secondary, #666);
    }
    .nav-item[aria-selected="true"] {
      color: var(--shenas-accent, #728F67);
      font-weight: 600;
    }
    .nav-item svg {
      flex-shrink: 0;
    }
    .hotkey-hint {
      font-size: 0.5rem;
      color: var(--shenas-text-faint, #ccc);
      font-family: monospace;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._components = [];
    this._activeIndex = 0;
    this._loading = true;
    this._loadedScripts = new Set();
    this._hotkeys = {};
    this._elementCache = new Map();
    this._paletteOpen = false;
    this._paletteCommands = [];
    this._uis = [];
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this._keyHandler = (e) => this._onKeydown(e);
    document.addEventListener("keydown", this._keyHandler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener("keydown", this._keyHandler);
  }

  async _fetchData() {
    this._loading = true;
    try {
      const resp = await fetch(`${this.apiBase}/graphql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: `{ components hotkeys theme { css } uis: plugins(kind: "ui") { name displayName enabled } }` }),
      });
      const json = await resp.json();
      const data = json.data;
      this._components = data?.components || [];
      this._hotkeys = data?.hotkeys || {};
      this._uis = data?.uis || [];

      // Apply theme
      if (data?.theme?.css && !document.querySelector("link[data-shenas-theme]")) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.setAttribute("data-shenas-theme", "");
        link.href = data.theme.css;
        document.head.appendChild(link);
      }
    } catch (e) {
      console.error("Failed to fetch data:", e);
    }
    this._loading = false;
    this._buildCommands();
  }

  _buildCommands() {
    const cmds = this._components.map((c, i) => ({
      id: `nav:${c.name}`,
      category: "Navigate",
      label: c.display_name || c.name,
      action: () => { this._activeIndex = i; },
    }));
    for (const ui of this._uis) {
      const label = ui.displayName || ui.name;
      cmds.push({
        id: `ui:${ui.name}`,
        category: "Switch UI",
        label: `${label}${ui.enabled ? " (active)" : ""}`,
        action: () => this._switchUI(ui.name),
      });
    }
    cmds.push(
      { id: "command-palette", category: "System", label: "Command Palette", action: () => { this._paletteOpen = true; } },
    );
    this._paletteCommands = cmds;
  }

  async _switchUI(name) {
    await fetch(`${this.apiBase}/graphql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `mutation($k: String!, $n: String!) { enablePlugin(kind: $k, name: $n) { ok } }`,
        variables: { k: "ui", n: name },
      }),
    });
    window.location.reload();
  }

  _onKeydown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "p") {
      e.preventDefault();
      this._paletteOpen = !this._paletteOpen;
      return;
    }
    // Navigate between components with hotkeys
    if (e.ctrlKey || e.metaKey) {
      const num = parseInt(e.key);
      if (num >= 1 && num <= this._components.length) {
        e.preventDefault();
        this._activeIndex = num - 1;
        return;
      }
    }

    // Check custom hotkey bindings
    for (const [actionId, binding] of Object.entries(this._hotkeys)) {
      if (!binding) continue;
      const parts = binding.split("+").map((s) => s.trim().toLowerCase());
      const ctrl = parts.includes("ctrl") || parts.includes("cmd");
      const shift = parts.includes("shift");
      const alt = parts.includes("alt");
      const key = parts.filter((p) => !["ctrl", "cmd", "shift", "alt"].includes(p))[0] || "";

      const eCtrl = e.ctrlKey || e.metaKey;
      if (eCtrl === ctrl && e.shiftKey === shift && e.altKey === alt && e.key.toLowerCase() === key) {
        e.preventDefault();
        // Handle navigation hotkeys
        const navMatch = actionId.match(/^nav:(.+)$/);
        if (navMatch) {
          const idx = this._components.findIndex((c) => c.name === navMatch[1]);
          if (idx >= 0) this._activeIndex = idx;
        }
        return;
      }
    }
  }

  _getOrCreateElement(comp) {
    if (!this._elementCache.has(comp.name)) {
      const el = document.createElement(comp.tag);
      el.setAttribute("api-base", this.apiBase);
      this._elementCache.set(comp.name, el);
    }
    return this._elementCache.get(comp.name);
  }

  _switchTo(index) {
    this._activeIndex = index;
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">Loading...</div>`;
    }

    if (this._components.length === 0) {
      return html`<div class="empty">
        <p>No components installed.</p>
      </div>`;
    }

    const comp = this._components[this._activeIndex];
    if (comp && !this._loadedScripts.has(comp.js)) {
      this._loadedScripts = new Set([...this._loadedScripts, comp.js]);
      const script = document.createElement("script");
      script.type = "module";
      script.src = comp.js;
      document.head.appendChild(script);
    }

    return html`
      <div class="content">
        ${comp ? html`<div class="component-host">${this._getOrCreateElement(comp)}</div>` : ""}
      </div>
      <shenas-job-panel></shenas-job-panel>
      <nav class="bottom-nav">
        ${this._components.map((c, i) => html`
          <button class="nav-item" aria-selected=${i === this._activeIndex}
            @click=${() => this._switchTo(i)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            <span>${c.display_name || c.name}</span>
            ${i < 9 ? html`<span class="hotkey-hint">Ctrl+${i + 1}</span>` : ""}
          </button>
        `)}
      </nav>
      <shenas-command-palette
        ?open=${this._paletteOpen}
        .commands=${this._paletteCommands}
        @execute=${(e) => { const cmd = e.detail; if (cmd.action) cmd.action(); this._paletteOpen = false; }}
        @close=${() => { this._paletteOpen = false; }}
      ></shenas-command-palette>
    `;
  }
}

customElements.define("shenas-focus", FocusApp);
