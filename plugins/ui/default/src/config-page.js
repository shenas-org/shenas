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
    _freqNum: { state: true },
    _freqUnit: { state: true },
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

  static _UNIT_MULTIPLIERS = { seconds: 1 / 60, minutes: 1, hours: 60, days: 1440 };

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
    this._freqNum = "";
    this._freqUnit = "hours";
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
    if (key === "sync_frequency" && currentValue) {
      const mins = parseFloat(currentValue);
      if (mins >= 1440 && mins % 1440 === 0) {
        this._freqNum = String(mins / 1440);
        this._freqUnit = "days";
      } else if (mins >= 60 && mins % 60 === 0) {
        this._freqNum = String(mins / 60);
        this._freqUnit = "hours";
      } else if (mins >= 1) {
        this._freqNum = String(mins);
        this._freqUnit = "minutes";
      } else {
        this._freqNum = String(mins * 60);
        this._freqUnit = "seconds";
      }
    } else if (key === "sync_frequency") {
      this._freqNum = "";
      this._freqUnit = "hours";
    }
  }

  _cancelEdit() {
    this._editing = null;
    this._editValue = "";
  }

  _freqToMinutes() {
    const num = parseFloat(this._freqNum);
    if (isNaN(num) || num <= 0) return null;
    return String(Math.round(num * ConfigPage._UNIT_MULTIPLIERS[this._freqUnit]));
  }

  _formatFreq(minutes) {
    const m = parseFloat(minutes);
    if (isNaN(m)) return minutes;
    if (m >= 1440 && m % 1440 === 0) return `${m / 1440} day${m / 1440 !== 1 ? "s" : ""}`;
    if (m >= 60 && m % 60 === 0) return `${m / 60} hour${m / 60 !== 1 ? "s" : ""}`;
    if (m >= 1) return `${m} minute${m !== 1 ? "s" : ""}`;
    return `${m * 60} second${m * 60 !== 1 ? "s" : ""}`;
  }

  async _saveEdit(key) {
    const value = key === "sync_frequency" ? this._freqToMinutes() : this._editValue;
    if (key === "sync_frequency" && value === null) {
      this._message = { type: "error", text: "Enter a positive number" };
      return;
    }
    const { ok, data } = await apiFetchFull(this.apiBase, `/config/${this.kind}/${this.name}`, {
      method: "PUT",
      json: { key, value },
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

  _renderFreqEdit(entry) {
    return html`
      <div class="edit-row">
        <input class="config-input" type="number" min="0" step="any" style="width: 80px"
          .value=${this._freqNum}
          @input=${(ev) => { this._freqNum = ev.target.value; }}
          @keydown=${(ev) => { if (ev.key === "Enter") this._saveEdit(entry.key); if (ev.key === "Escape") this._cancelEdit(); }}
        />
        <select @change=${(ev) => { this._freqUnit = ev.target.value; }}>
          ${Object.keys(ConfigPage._UNIT_MULTIPLIERS).map((u) => html`
            <option value=${u} ?selected=${this._freqUnit === u}>${u}</option>
          `)}
        </select>
        <button @click=${() => this._saveEdit(entry.key)}>Save</button>
        <button @click=${this._cancelEdit}>Cancel</button>
      </div>`;
  }

  _renderEntry(entry) {
    const isEditing = this._editing === entry.key;
    const isFreq = entry.key === "sync_frequency";
    const displayValue = isFreq && entry.value ? this._formatFreq(entry.value) : entry.value;
    return html`
      <div class="config-row">
        <div class="config-key">${entry.label || entry.key}</div>
        ${isEditing
          ? (isFreq ? this._renderFreqEdit(entry) : html`
            <div class="edit-row">
              <input class="config-input"
                .value=${this._editValue}
                @input=${(ev) => { this._editValue = ev.target.value; }}
                @keydown=${(ev) => { if (ev.key === "Enter") this._saveEdit(entry.key); if (ev.key === "Escape") this._cancelEdit(); }}
              />
              <button @click=${() => this._saveEdit(entry.key)}>Save</button>
              <button @click=${this._cancelEdit}>Cancel</button>
            </div>`)
          : html`
            <div class="config-detail">
              <div class="config-value ${displayValue ? "" : "empty"}"
                @click=${() => this._startEdit(entry.key, entry.value)}
                style="cursor: pointer"
                title="Click to edit"
              >${displayValue || "not set"}</div>
              ${entry.description ? html`<div class="config-desc">${entry.description}</div>` : ""}
            </div>`}
      </div>
    `;
  }
}

customElements.define("shenas-config", ConfigPage);
