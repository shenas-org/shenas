import { LitElement, html, css } from "lit";

const PLUGIN_KINDS = [
  { id: "pipe", label: "Pipes" },
  { id: "schema", label: "Schemas" },
  { id: "component", label: "Components" },
  { id: "ui", label: "UI" },
];

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    activeKind: { type: String, attribute: "active-kind" },
    onNavigate: { type: Function },
    _plugins: { state: true },
    _loading: { state: true },
    _actionMessage: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    .layout {
      display: flex;
      gap: 2rem;
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
    .sidebar button {
      display: block;
      width: 100%;
      text-align: left;
      padding: 0.5rem 0.8rem;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 0.9rem;
      color: #666;
      border-radius: 4px;
      border-left: 3px solid transparent;
    }
    .sidebar button:hover {
      background: #f5f5f5;
      color: #222;
    }
    .sidebar button[aria-selected="true"] {
      background: #f0f4ff;
      color: #222;
      font-weight: 600;
      border-left-color: #0066cc;
    }
    .content {
      flex: 1;
      min-width: 0;
    }
    .content h3 {
      font-size: 1rem;
      margin: 0 0 1rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th {
      text-align: left;
      padding: 0.4rem 0.6rem;
      color: #666;
      font-weight: 500;
      border-bottom: 1px solid #e0e0e0;
    }
    td {
      padding: 0.4rem 0.6rem;
      border-bottom: 1px solid #f0f0f0;
    }
    .name {
      font-weight: 600;
    }
    .version {
      color: #888;
      font-family: monospace;
      font-size: 0.85rem;
    }
    .desc {
      color: #555;
      max-width: 300px;
    }
    .actions {
      white-space: nowrap;
    }
    button.action {
      padding: 0.3rem 0.7rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.8rem;
      margin-left: 0.3rem;
    }
    button.action:hover {
      background: #f5f5f5;
    }
    button.remove {
      color: #c00;
      border-color: #e8c0c0;
    }
    button.remove:hover {
      background: #fef0f0;
    }
    .install-row {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
      align-items: center;
    }
    .install-row input {
      padding: 0.4rem 0.6rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 0.85rem;
      flex: 1;
      max-width: 200px;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-bottom: 1rem;
      font-size: 0.85rem;
    }
    .message.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .message.error {
      background: #fce4ec;
      color: #c62828;
    }
    .empty {
      color: #888;
      padding: 0.5rem 0;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this.activeKind = "pipe";
    this.onNavigate = null;
    this._plugins = {};
    this._loading = true;
    this._actionMessage = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchAll();
  }

  _selectKind(kind) {
    this._actionMessage = null;
    if (this.onNavigate) {
      this.onNavigate(kind);
    }
  }

  async _fetchAll() {
    this._loading = true;
    const result = {};
    await Promise.all(
      PLUGIN_KINDS.map(async ({ id }) => {
        const resp = await fetch(`${this.apiBase}/plugins/${id}`);
        result[id] = resp.ok ? await resp.json() : [];
      }),
    );
    this._plugins = result;
    this._loading = false;
  }

  async _remove(kind, name) {
    this._actionMessage = null;
    const resp = await fetch(`${this.apiBase}/plugins/${kind}/${name}`, {
      method: "DELETE",
    });
    const data = await resp.json();
    if (data.ok) {
      this._actionMessage = { type: "success", text: data.message };
      await this._fetchAll();
    } else {
      this._actionMessage = {
        type: "error",
        text: data.message || "Remove failed",
      };
    }
  }

  async _install(kind) {
    const input = this.shadowRoot.querySelector(`#install-${kind}`);
    const name = input?.value?.trim();
    if (!name) return;
    this._actionMessage = null;
    const resp = await fetch(`${this.apiBase}/plugins/${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names: [name], skip_verify: true }),
    });
    const data = await resp.json();
    const result = data.results?.[0];
    if (result?.ok) {
      this._actionMessage = { type: "success", text: result.message };
      input.value = "";
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
      ${this._actionMessage
        ? html`<div class="message ${this._actionMessage.type}">
            ${this._actionMessage.text}
          </div>`
        : ""}
      <div class="layout">
        <nav class="sidebar">
          <ul>
            ${PLUGIN_KINDS.map(
              ({ id, label }) => html`
                <li>
                  <button
                    aria-selected=${this.activeKind === id}
                    @click=${() => this._selectKind(id)}
                  >
                    ${label}
                    <span style="color:#aaa; font-weight:normal">
                      (${(this._plugins[id] || []).length})
                    </span>
                  </button>
                </li>
              `,
            )}
          </ul>
        </nav>
        <div class="content">${this._renderKind(this.activeKind)}</div>
      </div>
    `;
  }

  _renderKind(kind) {
    const plugins = this._plugins[kind] || [];
    const label = PLUGIN_KINDS.find((k) => k.id === kind)?.label || kind;
    return html`
      <h3>${label}</h3>
      ${plugins.length > 0
        ? html`
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Description</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${plugins.map(
                  (p) => html`
                    <tr>
                      <td class="name">${p.name}</td>
                      <td class="version">${p.version}</td>
                      <td class="desc">${p.description || ""}</td>
                      <td class="actions">
                        <button
                          class="action remove"
                          @click=${() => this._remove(kind, p.name)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  `,
                )}
              </tbody>
            </table>
          `
        : html`<p class="empty">No ${label.toLowerCase()} installed</p>`}
      <div class="install-row">
        <input
          id="install-${kind}"
          type="text"
          placeholder="Plugin name"
          @keydown=${(e) => e.key === "Enter" && this._install(kind)}
        />
        <button class="action" @click=${() => this._install(kind)}>
          Install
        </button>
      </div>
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
