import { LitElement, html, css } from "lit";
import { buttonStyles, messageStyles, utilityStyles } from "./shared-styles.js";

class ConfigPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    _config: { state: true },
    _loading: { state: true },
    _message: { state: true },
    _editing: { state: true },
    _editValue: { state: true },
  };

  static styles = [
    buttonStyles,
    messageStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .config-row {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.9rem;
        gap: 1rem;
      }
      .config-row:last-child {
        border-bottom: none;
      }
      .config-key {
        min-width: 140px;
        font-weight: 600;
        color: var(--shenas-text, #222);
        flex-shrink: 0;
      }
      .config-value {
        flex: 1;
        color: var(--shenas-text-secondary, #666);
        font-family: monospace;
        font-size: 0.85rem;
      }
      .config-value.empty {
        color: var(--shenas-text-faint, #aaa);
        font-style: italic;
        font-family: inherit;
      }
      .config-desc {
        font-size: 0.8rem;
        color: var(--shenas-text-muted, #888);
        margin-top: 0.2rem;
      }
      .config-detail {
        flex: 1;
      }
      input.config-input {
        width: 100%;
        padding: 0.3rem 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
        box-sizing: border-box;
      }
      .edit-row {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex: 1;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this._config = null;
    this._loading = true;
    this._message = null;
    this._editing = null;
    this._editValue = "";
  }

  willUpdate(changed) {
    if (changed.has("kind") || changed.has("name")) {
      this._fetchConfig();
    }
  }

  async _fetchConfig() {
    if (!this.kind || !this.name) return;
    this._loading = true;
    const resp = await fetch(`${this.apiBase}/config?kind=${this.kind}&name=${this.name}`);
    if (resp.ok) {
      const items = await resp.json();
      this._config = items.length > 0 ? items[0] : null;
    } else {
      this._config = null;
    }
    this._loading = false;
  }

  _startEdit(key, currentValue) {
    this._editing = key;
    this._editValue = currentValue || "";
  }

  _cancelEdit() {
    this._editing = null;
    this._editValue = "";
  }

  async _saveEdit(key) {
    const resp = await fetch(`${this.apiBase}/config/${this.kind}/${this.name}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: this._editValue }),
    });
    if (resp.ok) {
      this._message = { type: "success", text: `Updated ${key}` };
      this._editing = null;
      await this._fetchConfig();
    } else {
      const data = await resp.json();
      this._message = { type: "error", text: data.detail || "Update failed" };
    }
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading config...</p>`;
    }
    if (!this._config || this._config.entries.length === 0) {
      return html`<p class="empty">No configuration settings for this plugin.</p>`;
    }

    return html`
      ${this._message
        ? html`<div class="message ${this._message.type}">${this._message.text}</div>`
        : ""}
      ${this._config.entries.map((e) => this._renderEntry(e))}
    `;
  }

  _renderEntry(entry) {
    const isEditing = this._editing === entry.key;
    return html`
      <div class="config-row">
        <div class="config-key">${entry.key}</div>
        ${isEditing
          ? html`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${(ev) => { this._editValue = ev.target.value; }}
                @keydown=${(ev) => { if (ev.key === "Enter") this._saveEdit(entry.key); if (ev.key === "Escape") this._cancelEdit(); }}
              />
              <button @click=${() => this._saveEdit(entry.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`
          : html`
            <div class="config-detail">
              <div class="config-value ${entry.value ? "" : "empty"}"
                @click=${() => this._startEdit(entry.key, entry.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${entry.value || "not set"}</div>
              ${entry.description ? html`<div class="config-desc">${entry.description}</div>` : ""}
            </div>`}
      </div>
    `;
  }
}

customElements.define("shenas-config", ConfigPage);
