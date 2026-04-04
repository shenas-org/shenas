import { LitElement, html, css } from "lit";
import { apiFetch, apiFetchFull, renderMessage } from "./api.js";
import { PLUGIN_KINDS } from "./constants.js";
import { buttonStyles, formStyles, linkStyles, messageStyles } from "./shared-styles.js";

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeKind: { type: String, attribute: "active-kind" },
    onNavigate: { type: Function },
    allActions: { type: Array },
    _plugins: { state: true },
    _loading: { state: true },
    _actionMessage: { state: true },
    _installing: { state: true },
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
    const result = {};
    await Promise.all(
      PLUGIN_KINDS.map(async ({ id }) => {
        result[id] = (await apiFetch(this.apiBase, `/plugins/${id}`)) || [];
      }),
    );
    this._plugins = result;
    this._loading = false;
  }



  async _togglePlugin(kind, name, currentlyEnabled) {
    const action = currentlyEnabled ? "disable" : "enable";
    const { data } = await apiFetchFull(this.apiBase, `/plugins/${kind}/${name}/${action}`, { method: "POST" });
    if (!data?.ok) {
      this._actionMessage = { type: "error", text: data?.message || `${action} failed` };
    }
    if (kind === "theme") {
      await this._applyActiveTheme();
    }
    await this._fetchAll();
  }

  async _applyActiveTheme() {
    const data = await apiFetch(this.apiBase, `/theme`);
    if (!data) return;
    const { css } = data;
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

  async _install(kind) {
    const input = this.shadowRoot.querySelector(`#install-${kind}`);
    const name = input?.value?.trim();
    if (!name) return;
    this._actionMessage = null;
    const { data } = await apiFetchFull(this.apiBase, `/plugins/${kind}`, {
      method: "POST",
      json: { names: [name], skip_verify: true },
    });
    const result = data?.results?.[0];
    if (result?.ok) {
      this._actionMessage = { type: "success", text: result.message };
      this._installing = false;
      await this._fetchAll();
    } else {
      this._actionMessage = {
        type: "error",
        text: result?.message || "Install failed",
      };
    }
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
        <div class="layout">
        <button class="burger" @click=${() => { this._menuOpen = true; }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          ${this._displayName()}
        </button>
        <div class="menu-overlay ${this._menuOpen ? "open" : ""}" @click=${() => { this._menuOpen = false; }}></div>
        ${this._menuOpen ? html`
          <div class="menu-panel">
            <button class="menu-close" @click=${() => { this._menuOpen = false; }}>x</button>
            <a href="/settings/data-flow" aria-selected=${this.activeKind === "data-flow"}
              @click=${(e) => { e.preventDefault(); this._switchKind("data-flow"); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
              Data Flow
            </a>
            <a href="/settings/hotkeys" aria-selected=${this.activeKind === "hotkeys"}
              @click=${(e) => { e.preventDefault(); this._switchKind("hotkeys"); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="6" y1="8" x2="6" y2="8"/><line x1="10" y1="8" x2="10" y2="8"/><line x1="14" y1="8" x2="14" y2="8"/><line x1="18" y1="8" x2="18" y2="8"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="8" y1="16" x2="16" y2="16"/></svg>
              Hotkeys
            </a>
            <div class="sidebar-section">Plugins</div>
            ${PLUGIN_KINDS.map(({ id, label }) => html`
              <a href="/settings/${id}" aria-selected=${this.activeKind === id}
                @click=${(e) => { e.preventDefault(); this._switchKind(id); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.5 2H3.5C2.67 2 2 2.67 2 3.5v17C2 21.33 2.67 22 3.5 22h17c.83 0 1.5-.67 1.5-1.5v-17C22 2.67 21.33 2 20.5 2zM8 19H5v-3h3v3zm0-5H5v-3h3v3zm0-5H5V6h3v3z"/></svg>
                ${label} (${(this._plugins[id] || []).length})
              </a>
            `)}
          </div>
        ` : ""}
        <nav class="sidebar">
          <ul>
            <li>
              <a href="/settings/data-flow" aria-selected=${this.activeKind === "data-flow"}
                @click=${(e) => { e.preventDefault(); this._switchKind("data-flow"); }}>
                Data Flow
              </a>
            </li>
            <li>
              <a href="/settings/hotkeys" aria-selected=${this.activeKind === "hotkeys"}
                @click=${(e) => { e.preventDefault(); this._switchKind("hotkeys"); }}>
                Hotkeys
              </a>
            </li>
          </ul>
          <div class="sidebar-section">Plugins</div>
          <ul>
            ${PLUGIN_KINDS.map(
              ({ id, label }) => html`
                <li>
                  <a
                    href="/settings/${id}"
                    aria-selected=${this.activeKind === id}
                    @click=${(e) => { e.preventDefault(); this._switchKind(id); }}
                  >
                    ${label}
                    <span style="color:var(--shenas-text-faint, #aaa); font-weight:normal">
                      (${(this._plugins[id] || []).length})
                    </span>
                  </a>
                </li>
              `,
            )}
          </ul>
        </nav>
        <div class="content">
          ${this.activeKind === "data-flow"
            ? html`<shenas-pipeline-overview api-base="${this.apiBase}"></shenas-pipeline-overview>`
            : this.activeKind === "hotkeys"
              ? html`<shenas-hotkeys api-base="${this.apiBase}" .actions=${this.allActions || []}></shenas-hotkeys>`
              : this._renderKind(this.activeKind)}
        </div>
      </div>
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
          { label: "Name", render: (p) => html`<a href="/settings/${kind}/${p.name}">${p.display_name || p.name}</a>` },
          { key: "version", label: "Version", class: "mono" },
          ...(kind === "pipe" ? [
            { label: "Sync Freq.", class: "mono", render: (p) => p.sync_frequency ? this._formatFreq(p.sync_frequency) : "" },
            { label: "Last Synced", class: "mono", render: (p) => p.synced_at ? p.synced_at.slice(0, 16).replace("T", " ") : "never" },
          ] : []),
          { label: "Status", render: (p) => kind === "pipe" && p.has_auth === false
            ? html`<span style="color:var(--shenas-error,#c62828);font-size:0.8rem">Needs Auth</span>`
            : html`<status-toggle ?enabled=${p.enabled !== false} toggleable @toggle=${() => this._togglePlugin(kind, p.name, p.enabled !== false)}></status-toggle>` },
        ]}
        .rows=${plugins}
        .rowClass=${(p) => p.enabled === false ? "disabled-row" : ""}
        ?show-add=${!this._installing}
        @add=${() => { this._installing = true; }}
        empty-text="No ${label.toLowerCase()} installed"
      ></shenas-data-list>
      ${this._installing
        ? html`<shenas-form-panel
            title="Install new plugin"
            submit-label="Install"
            @submit=${() => this._install(kind)}
            @cancel=${() => { this._installing = false; }}
          >
            <div class="field">
              <input
                id="install-${kind}"
                type="text"
                placeholder="Plugin name"
                @keydown=${(e) => e.key === "Enter" && this._install(kind)}
              />
            </div>
          </shenas-form-panel>`
        : ""}
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
