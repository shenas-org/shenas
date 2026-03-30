import { LitElement, html, css } from "lit";
import { apiFetch, apiFetchFull, renderMessage } from "./api.js";
import { PLUGIN_KINDS } from "./constants.js";
import { buttonStyles, linkStyles, messageStyles, utilityStyles } from "./shared-styles.js";

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeKind: { type: String, attribute: "active-kind" },
    onNavigate: { type: Function },
    _plugins: { state: true },
    _loading: { state: true },
    _actionMessage: { state: true },
    _installing: { state: true },
  };

  static styles = [
    buttonStyles,
    linkStyles,
    messageStyles,
    utilityStyles,
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
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.activeKind = "pipe";
    this.onNavigate = null;
    this._plugins = {};
    this._loading = true;
    this._actionMessage = null;
    this._installing = false;
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

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading plugins...</p>`;
    }

    return html`
      ${renderMessage(this._actionMessage)}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            <li>
              <a href="/settings/overview" aria-selected=${this.activeKind === "overview"}>
                Data Flow
              </a>
            </li>
            ${PLUGIN_KINDS.map(
              ({ id, label }) => html`
                <li>
                  <a
                    href="/settings/${id}"
                    aria-selected=${this.activeKind === id}
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
          ${this.activeKind === "overview"
            ? html`<shenas-pipeline-overview api-base="${this.apiBase}"></shenas-pipeline-overview>`
            : this._renderKind(this.activeKind)}
        </div>
      </div>
    `;
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
          { label: "Added", class: "mono", render: (p) => p.added_at ? p.added_at.slice(0, 10) : "" },
          { label: "Status", render: (p) => html`<status-toggle ?enabled=${p.enabled !== false} toggleable @toggle=${() => this._togglePlugin(kind, p.name, p.enabled !== false)}></status-toggle>` },
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
            <input
              id="install-${kind}"
              type="text"
              placeholder="Plugin name"
              @keydown=${(e) => e.key === "Enter" && this._install(kind)}
              style="width: 100%; padding: 0.4rem 0.6rem; border: 1px solid var(--shenas-border-input, #ddd); border-radius: 4px; font-size: 0.85rem; box-sizing: border-box; background: var(--shenas-bg, #fff); color: var(--shenas-text, #222);"
            />
          </shenas-form-panel>`
        : ""}
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
