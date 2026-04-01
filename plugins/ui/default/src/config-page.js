import { LitElement, html, css } from "lit";
import { apiFetch, apiFetchFull, renderMessage } from "./api.js";
import { buttonStyles, formStyles, messageStyles } from "./shared-styles.js";

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
    formStyles,
    messageStyles,
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
      .config-input {
        font-family: monospace;
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
    const items = await apiFetch(this.apiBase, `/config?kind=${this.kind}&name=${this.name}`);
    this._config = items && items.length > 0 ? items[0] : null;
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
    const { ok, data } = await apiFetchFull(this.apiBase, `/config/${this.kind}/${this.name}`, {
      method: "PUT",
      json: { key, value: this._editValue },
    });
    if (ok) {
      this._message = { type: "success", text: `Updated ${key}` };
      this._editing = null;
      await this._fetchConfig();
    } else {
      this._message = { type: "error", text: data?.detail || "Update failed" };
    }
  }

  render() {
    const empty = !this._config || this._config.entries.length === 0;
    return html`
      <shenas-page ?loading=${this._loading} ?empty=${empty}
        loading-text="Loading config..." empty-text="No configuration settings for this plugin.">
        ${renderMessage(this._message)}
        ${this._config?.entries.map((e) => this._renderEntry(e))}
      </shenas-page>
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
