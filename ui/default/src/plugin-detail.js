import { LitElement, html, css } from "lit";
import { buttonStyles, linkStyles, messageStyles, tabStyles, utilityStyles } from "./shared-styles.js";

class PluginDetail extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    activeTab: { type: String, attribute: "active-tab" },
    _info: { state: true },
    _loading: { state: true },
    _message: { state: true },
    _hasConfig: { state: true },
    _hasAuth: { state: true },
    _tables: { state: true },
    _syncing: { state: true },
  };

  static styles = [
    buttonStyles,
    linkStyles,
    messageStyles,
    tabStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .back {
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
      }
      .title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .title-actions {
        display: flex;
        gap: 0.5rem;
      }
      h2 {
        margin: 0;
        font-size: 1.3rem;
      }
      .kind-badge {
        background: #f0f0f0;
        color: #555;
        padding: 0.15rem 0.5rem;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 400;
        vertical-align: middle;
        margin-left: 0.3rem;
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
      button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
      .section-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        color: #888;
        letter-spacing: 0.05em;
        margin: 1.5rem 0 0.5rem;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this.activeTab = "details";
    this._info = null;
    this._loading = true;
    this._message = null;
    this._hasConfig = false;
    this._hasAuth = false;
    this._tables = [];
    this._syncing = false;
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
    const [configResp, authResp, dbResp] = await Promise.all([
      fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`),
      this.kind === "pipe"
        ? fetch(`${this.apiBase}/auth/${this.name}/fields`)
        : Promise.resolve(null),
      this.kind === "pipe"
        ? fetch(`${this.apiBase}/db/status`)
        : Promise.resolve(null),
    ]);
    if (configResp.ok) {
      const items = await configResp.json();
      this._hasConfig = items.length > 0 && items[0].entries.length > 0;
    }
    if (authResp?.ok) {
      const data = await authResp.json();
      this._hasAuth = (data.fields?.length > 0) || !!data.instructions;
    }
    if (dbResp?.ok) {
      const db = await dbResp.json();
      const schema = (db.schemas || []).find((s) => s.name === this.name);
      this._tables = schema ? schema.tables.filter((t) => !t.name.startsWith("_dlt_")) : [];
    }
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

  async _sync() {
    this._syncing = true;
    this._message = null;
    try {
      const resp = await fetch(`${this.apiBase}/sync/${this.name}`, { method: "POST" });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        this._message = { type: "error", text: data.detail || `Sync failed (${resp.status})` };
        this._syncing = false;
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let lastEvent = "";
      let lastData = "";
      let hadError = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (line.startsWith("event: ")) lastEvent = line.slice(7).trim();
          if (line.startsWith("data: ")) lastData = line.slice(6);
        }
        if (lastEvent === "error") hadError = true;
      }
      let msg = "Sync complete";
      try { msg = JSON.parse(lastData).message || msg; } catch { /* use default */ }
      this._message = { type: hadError ? "error" : "success", text: msg };
      if (!hadError) await this._fetchInfo();
    } catch (e) {
      this._message = { type: "error", text: `Sync failed: ${e.message}` };
    }
    this._syncing = false;
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

      <div class="title-row">
        <h2>${info.display_name || info.name} <span class="kind-badge">${info.kind}</span></h2>
        <div class="title-actions">
          ${this.kind === "pipe" && enabled
            ? html`<button @click=${this._sync} ?disabled=${this._syncing}>${this._syncing ? "Syncing..." : "Sync"}</button>`
            : ""}
          <button class="danger" @click=${this._remove}>Remove</button>
        </div>
      </div>

      ${this._hasConfig || this._hasAuth
        ? html`
          <div class="tabs">
            <a class="tab" href="${basePath}" aria-selected=${this.activeTab === "details"}>Details</a>
            ${this._hasConfig
              ? html`<a class="tab" href="${basePath}/config" aria-selected=${this.activeTab === "config"}>Config</a>`
              : ""}
            ${this._hasAuth
              ? html`<a class="tab" href="${basePath}/auth" aria-selected=${this.activeTab === "auth"}>Auth</a>`
              : ""}
          </div>`
        : ""}

      ${this.activeTab === "config" && this._hasConfig
        ? html`<shenas-config api-base="${this.apiBase}" kind="${this.kind}" name="${this.name}"></shenas-config>`
        : this.activeTab === "auth" && this._hasAuth
          ? html`<shenas-auth api-base="${this.apiBase}" pipe-name="${this.name}"></shenas-auth>`
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
            <status-toggle ?enabled=${enabled} toggleable @toggle=${this._toggle}></status-toggle>
          </span>
        </div>
        ${this._stateRow("Last synced", info.synced_at)}
        ${this._stateRow("Added", info.added_at)}
        ${this._stateRow("Updated", info.updated_at)}
        ${this._stateRow("Status changed", info.status_changed_at)}
      </div>

      ${this.kind === "pipe"
        ? html`
          <h4 class="section-title">Resources</h4>
          <shenas-data-list
            .columns=${[
              { key: "name", label: "Table", class: "mono" },
              { key: "rows", label: "Rows", class: "muted" },
              { label: "Range", class: "muted", render: (t) => t.earliest ? `${t.earliest} - ${t.latest}` : "" },
            ]}
            .rows=${this._tables}
            empty-text="No tables synced yet"
          ></shenas-data-list>`
        : ""}

      ${this.kind === "pipe"
        ? html`
          <h4 class="section-title">Transforms</h4>
          <shenas-transforms api-base="${this.apiBase}" source="${this.name}"></shenas-transforms>`
        : ""}

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
