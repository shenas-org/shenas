import { LitElement, html, css } from "lit";

class PluginDetail extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    activeTab: { type: String, attribute: "active-tab" },
    _info: { state: true },
    _loading: { state: true },
    _message: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    .back {
      color: #0066cc;
      text-decoration: none;
      font-size: 0.9rem;
      display: inline-block;
      margin-bottom: 1rem;
    }
    .back:hover {
      text-decoration: underline;
    }
    h2 {
      margin: 0 0 0.3rem;
      font-size: 1.3rem;
    }
    .kind-badge {
      display: inline-block;
      background: #f0f0f0;
      color: #555;
      padding: 0.15rem 0.5rem;
      border-radius: 3px;
      font-size: 0.8rem;
      margin-bottom: 1rem;
    }
    .description {
      color: #444;
      line-height: 1.6;
      margin: 1rem 0;
      white-space: pre-line;
    }
    .state-table {
      margin: 1.5rem 0;
    }
    .state-row {
      display: flex;
      padding: 0.4rem 0;
      border-bottom: 1px solid #f0f0f0;
      font-size: 0.9rem;
    }
    .state-row:last-child {
      border-bottom: none;
    }
    .state-label {
      width: 120px;
      color: #888;
      flex-shrink: 0;
    }
    .state-value {
      color: #333;
    }
    .enabled {
      color: #2e7d32;
      font-weight: 600;
    }
    .disabled {
      color: #c62828;
      font-weight: 600;
    }
    .actions {
      display: flex;
      gap: 0.6rem;
      margin-top: 1.5rem;
    }
    button {
      padding: 0.5rem 1rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 0.9rem;
    }
    button:hover {
      background: #f5f5f5;
    }
    button.danger {
      color: #c00;
      border-color: #e8c0c0;
    }
    button.danger:hover {
      background: #fef0f0;
    }
    .detail-tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid #e0e0e0;
      margin: 1rem 0;
    }
    .detail-tab {
      padding: 0.5rem 1rem;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 0.9rem;
      color: #666;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      text-decoration: none;
    }
    .detail-tab:hover {
      color: #222;
    }
    .detail-tab[aria-selected="true"] {
      color: #222;
      border-bottom-color: #0066cc;
      font-weight: 600;
    }
    .message {
      padding: 0.5rem 0.8rem;
      border-radius: 4px;
      margin-top: 1rem;
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
    .loading {
      color: #888;
      font-style: italic;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this.activeTab = "details";
    this._info = null;
    this._loading = true;
    this._message = null;
  }

  willUpdate(changed) {
    if (changed.has("kind") || changed.has("name")) {
      this._fetchInfo();
    }
  }

  async _fetchInfo() {
    if (!this.kind || !this.name) return;
    this._loading = true;
    this._message = null;
    const resp = await fetch(
      `${this.apiBase}/plugins/${this.kind}/${this.name}/info`,
    );
    this._info = resp.ok ? await resp.json() : null;
    this._loading = false;
  }

  async _toggle() {
    const action = this._info?.enabled !== false ? "disable" : "enable";
    const resp = await fetch(
      `${this.apiBase}/plugins/${this.kind}/${this.name}/${action}`,
      { method: "POST" },
    );
    const data = await resp.json();
    this._message = {
      type: data.ok ? "success" : "error",
      text: data.message || `${action} failed`,
    };
    await this._fetchInfo();
    this.dispatchEvent(new CustomEvent("plugin-state-changed", { bubbles: true, composed: true }));
  }

  async _remove() {
    const resp = await fetch(
      `${this.apiBase}/plugins/${this.kind}/${this.name}`,
      { method: "DELETE" },
    );
    const data = await resp.json();
    if (data.ok) {
      window.history.pushState({}, "", `/settings/${this.kind}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    } else {
      this._message = { type: "error", text: data.message || "Remove failed" };
    }
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading...</p>`;
    }
    if (!this._info) {
      return html`<p>Plugin not found.</p>`;
    }

    const info = this._info;
    const enabled = info.enabled !== false;

    const basePath = `/settings/${this.kind}/${this.name}`;

    return html`
      <a class="back" href="/settings/${this.kind}">&larr; Back to ${this.kind}s</a>

      <h2>${info.display_name || info.name}</h2>
      <span class="kind-badge">${info.kind}</span>

      <div class="detail-tabs">
        <a class="detail-tab" href="${basePath}" aria-selected=${this.activeTab === "details"}>Details</a>
        ${this.kind === "pipe"
          ? html`<a class="detail-tab" href="${basePath}/transforms" aria-selected=${this.activeTab === "transforms"}>Transforms</a>`
          : ""}
      </div>

      ${this.activeTab === "transforms"
        ? html`<shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`
        : this._renderDetails(info, enabled)}

      ${this._message
        ? html`<div class="message ${this._message.type}">
            ${this._message.text}
          </div>`
        : ""}
    `;
  }

  _renderDetails(info, enabled) {
    return html`
      ${info.description
        ? html`<div class="description">${info.description}</div>`
        : ""}

      <div class="state-table">
        <div class="state-row">
          <span class="state-label">Status</span>
          <span class="state-value">
            <status-dot ?enabled=${enabled}></status-dot>
          </span>
        </div>
        ${this._stateRow("Added", info.added_at)}
        ${this._stateRow("Updated", info.updated_at)}
        ${this._stateRow("Status changed", info.status_changed_at)}
      </div>

      <div class="actions">
        <button @click=${this._toggle}>
          ${enabled ? "Disable" : "Enable"}
        </button>
        <button class="danger" @click=${this._remove}>Remove</button>
      </div>
    `;
  }

  _stateRow(label, value) {
    if (!value) return "";
    return html`
      <div class="state-row">
        <span class="state-label">${label}</span>
        <span class="state-value">${value.slice(0, 19)}</span>
      </div>
    `;
  }
}

customElements.define("shenas-plugin-detail", PluginDetail);
