import { LitElement, html, css } from "lit";
import { gql, gqlFull } from "./api.js";
import { buttonStyles, messageStyles, utilityStyles } from "./shared-styles.js";
import { formatHotkey } from "./constants.js";

class HotkeysPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    actions: { type: Array },
    _bindings: { state: true },
    _recording: { state: true },
    _recordedKey: { state: true },
    _conflict: { state: true },
    _loading: { state: true },
    _filter: { state: true },
  };

  static styles = [
    buttonStyles,
    messageStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      .filter-input {
        padding: 0.3rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        width: 200px;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      .hotkey-row {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.85rem;
      }
      .hotkey-row:last-child {
        border-bottom: none;
      }
      .hotkey-category {
        min-width: 70px;
        color: var(--shenas-text-muted, #888);
        font-size: 0.75rem;
      }
      .hotkey-label {
        flex: 1;
        color: var(--shenas-text, #222);
      }
      .hotkey-binding {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
      }
      .kbd {
        display: inline-block;
        padding: 2px 8px;
        background: var(--shenas-bg-secondary, #fafafa);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--shenas-text, #222);
        min-width: 20px;
        text-align: center;
      }
      .unbound {
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.75rem;
      }
      .edit-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.75rem;
        padding: 2px 6px;
      }
      .edit-btn:hover {
        color: var(--shenas-primary, #0066cc);
      }
      .recording {
        padding: 2px 8px;
        background: var(--shenas-bg-selected, #f0f4ff);
        border: 2px solid var(--shenas-primary, #0066cc);
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--shenas-primary, #0066cc);
        min-width: 80px;
        text-align: center;
      }
      .conflict {
        font-size: 0.75rem;
        color: var(--shenas-error, #c62828);
        margin-left: 0.5rem;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.actions = [];
    this._bindings = {};
    this._recording = null;
    this._recordedKey = "";
    this._conflict = null;
    this._loading = true;
    this._filter = "";
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadBindings();
    this._boundKeydown = (e) => this._onKeydown(e);
    document.addEventListener("keydown", this._boundKeydown, true);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener("keydown", this._boundKeydown, true);
  }

  async _loadBindings() {
    this._loading = true;
    const data = await gql(this.apiBase, `{ hotkeys }`);
    this._bindings = data?.hotkeys || {};
    this._loading = false;
  }

  async _saveBinding(actionId, binding) {
    if (binding) {
      await gqlFull(this.apiBase, `mutation($id: String!, $b: String!) { setHotkey(actionId: $id, binding: $b) { ok } }`, { id: actionId, b: binding });
    } else {
      await gqlFull(this.apiBase, `mutation($id: String!) { deleteHotkey(actionId: $id) { ok } }`, { id: actionId });
    }
    this.dispatchEvent(new CustomEvent("hotkeys-changed", { bubbles: true, composed: true }));
  }

  _startRecording(actionId) {
    this._recording = actionId;
    this._recordedKey = "";
    this._conflict = null;
  }

  _stopRecording() {
    this._recording = null;
    this._recordedKey = "";
    this._conflict = null;
  }

  _onKeydown(e) {
    if (!this._recording) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.key === "Escape") { this._stopRecording(); return; }
    if (["Control", "Shift", "Alt", "Meta"].includes(e.key)) return;
    const combo = formatHotkey(e);
    this._recordedKey = combo;
    const conflict = Object.entries(this._bindings).find(
      ([id, b]) => b === combo && id !== this._recording,
    );
    this._conflict = conflict ? conflict[0] : null;
  }

  async _applyRecording() {
    if (!this._recordedKey || !this._recording) return;
    if (this._conflict) {
      this._bindings = { ...this._bindings, [this._conflict]: "" };
      await this._saveBinding(this._conflict, "");
    }
    this._bindings = { ...this._bindings, [this._recording]: this._recordedKey };
    await this._saveBinding(this._recording, this._recordedKey);
    this._stopRecording();
  }

  async _clearBinding(actionId) {
    this._bindings = { ...this._bindings, [actionId]: "" };
    await this._saveBinding(actionId, "");
  }

  async _resetDefaults() {
    await gqlFull(this.apiBase, `mutation { resetHotkeys { ok } }`);
    await this._loadBindings();
    this.dispatchEvent(new CustomEvent("hotkeys-changed", { bubbles: true, composed: true }));
  }

  _getActionLabel(actionId) {
    const action = this.actions.find((a) => a.id === actionId);
    return action ? action.label : actionId;
  }

  _getActionCategory(actionId) {
    const action = this.actions.find((a) => a.id === actionId);
    return action ? action.category : "";
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading hotkeys...</p>`;
    }

    const q = this._filter.toLowerCase();
    const filtered = this.actions.filter((a) =>
      !q || a.label.toLowerCase().includes(q) || a.category.toLowerCase().includes(q),
    );

    return html`
      <div class="toolbar">
        <button @click=${this._resetDefaults}>Reset to Defaults</button>
        <input class="filter-input" type="text" placeholder="Filter actions..."
          .value=${this._filter} @input=${(e) => { this._filter = e.target.value; }} />
      </div>
      ${filtered.map((a) => this._renderRow(a.id, a.label, a.category))}
    `;
  }

  _renderRow(actionId, label, category) {
    const binding = this._bindings[actionId] || "";
    const isRecording = this._recording === actionId;
    const conflictLabel = this._conflict ? this._getActionLabel(this._conflict) : "";

    return html`
      <div class="hotkey-row">
        <span class="hotkey-category">${category}</span>
        <span class="hotkey-label">${label}</span>
        <span class="hotkey-binding">
          ${isRecording
            ? html`
              <span class="recording">${this._recordedKey || "Press a key..."}</span>
              ${this._conflict ? html`<span class="conflict">Conflicts with ${conflictLabel}</span>` : ""}
              <button @click=${this._applyRecording} ?disabled=${!this._recordedKey}>Save</button>
              <button @click=${this._stopRecording}>Cancel</button>
            `
            : html`
              ${binding
                ? html`<span class="kbd">${binding}</span>`
                : html`<span class="unbound">-</span>`}
              <button class="edit-btn" @click=${() => this._startRecording(actionId)}>Edit</button>
              ${binding ? html`<button class="edit-btn" @click=${() => this._clearBinding(actionId)}>Clear</button>` : ""}
            `}
        </span>
      </div>
    `;
  }
}

customElements.define("shenas-hotkeys", HotkeysPage);
