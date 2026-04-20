import { LitElement, html, css } from "lit";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  buttonStyles,
  messageStyles,
  utilityStyles,
  formatHotkey,
  sortActions,
} from "shenas-frontends";
import { GET_HOTKEYS } from "./graphql/queries.ts";
import { SET_HOTKEY, DELETE_HOTKEY, RESET_HOTKEYS } from "./graphql/mutations.ts";

interface HotkeyAction {
  id: string;
  label: string;
  category: string;
}

class HotkeysPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    actions: { type: Array },
    _bindings: { state: true },
    _recording: { state: true },
    _recordedKey: { state: true },
    _conflict: { state: true },
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

  declare apiBase: string;
  declare actions: HotkeyAction[];
  declare _bindings: Record<string, string>;
  declare _recording: string | null;
  declare _recordedKey: string;
  declare _conflict: string | null;
  declare _filter: string;
  private _boundKeydown: ((e: KeyboardEvent) => void) | null = null;

  private _client = getClient();

  private _hotkeysQuery = new ApolloQueryController(this, GET_HOTKEYS, {
    client: this._client,
  });

  private _setHotkeyMutation = new ApolloMutationController(this, SET_HOTKEY, {
    client: this._client,
    refetchQueries: [{ query: GET_HOTKEYS }],
  });

  private _deleteHotkeyMutation = new ApolloMutationController(this, DELETE_HOTKEY, {
    client: this._client,
    refetchQueries: [{ query: GET_HOTKEYS }],
  });

  private _resetHotkeysMutation = new ApolloMutationController(this, RESET_HOTKEYS, {
    client: this._client,
    refetchQueries: [{ query: GET_HOTKEYS }],
  });

  private get _loading(): boolean {
    return this._hotkeysQuery.loading;
  }

  constructor() {
    super();
    this.apiBase = "/api";
    this.actions = [];
    this._bindings = {};
    this._recording = null;
    this._recordedKey = "";
    this._conflict = null;
    this._filter = "";
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._boundKeydown = (e: KeyboardEvent) => this._onKeydown(e);
    document.addEventListener("keydown", this._boundKeydown, true);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._boundKeydown) {
      document.removeEventListener("keydown", this._boundKeydown, true);
    }
  }

  private _lastQueryData: Record<string, string> | null = null;

  willUpdate(): void {
    const hotkeys = this._hotkeysQuery.data?.hotkeys as Record<string, string> | undefined;
    if (hotkeys && hotkeys !== this._lastQueryData) {
      this._lastQueryData = hotkeys;
      this._bindings = { ...hotkeys };
    }
  }

  async _saveBinding(actionId: string, binding: string): Promise<void> {
    if (binding) {
      await this._setHotkeyMutation.mutate({
        variables: { id: actionId, b: binding },
      });
    } else {
      await this._deleteHotkeyMutation.mutate({
        variables: { id: actionId },
      });
    }
    this.dispatchEvent(new CustomEvent("hotkeys-changed", { bubbles: true, composed: true }));
  }

  _startRecording(actionId: string): void {
    this._recording = actionId;
    this._recordedKey = "";
    this._conflict = null;
  }

  _stopRecording(): void {
    this._recording = null;
    this._recordedKey = "";
    this._conflict = null;
  }

  _onKeydown(e: KeyboardEvent): void {
    if (!this._recording) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.key === "Escape") {
      this._stopRecording();
      return;
    }
    if (["Control", "Shift", "Alt", "Meta"].includes(e.key)) return;
    const combo = formatHotkey(e);
    this._recordedKey = combo;
    const conflict = Object.entries(this._bindings).find(([id, b]) => b === combo && id !== this._recording);
    this._conflict = conflict ? conflict[0] : null;
  }

  async _applyRecording(): Promise<void> {
    if (!this._recordedKey || !this._recording) return;
    if (this._conflict) {
      this._bindings = { ...this._bindings, [this._conflict]: "" };
      await this._saveBinding(this._conflict, "");
    }
    this._bindings = { ...this._bindings, [this._recording]: this._recordedKey };
    await this._saveBinding(this._recording, this._recordedKey);
    this._stopRecording();
  }

  async _clearBinding(actionId: string): Promise<void> {
    this._bindings = { ...this._bindings, [actionId]: "" };
    await this._saveBinding(actionId, "");
  }

  async _resetDefaults(): Promise<void> {
    await this._resetHotkeysMutation.mutate();
    this._lastQueryData = null;
    this._hotkeysQuery.refetch();
    this.dispatchEvent(new CustomEvent("hotkeys-changed", { bubbles: true, composed: true }));
  }

  _getActionLabel(actionId: string): string {
    const action = this.actions.find((a) => a.id === actionId);
    return action ? action.label : actionId;
  }

  _getActionCategory(actionId: string): string {
    const action = this.actions.find((a) => a.id === actionId);
    return action ? action.category : "";
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading hotkeys...</p>`;
    }

    const q = this._filter.toLowerCase();
    const filtered = sortActions(
      this.actions.filter((a) => !q || a.label.toLowerCase().includes(q) || a.category.toLowerCase().includes(q)),
      this._bindings,
    ) as HotkeyAction[];

    return html`
      <div class="toolbar">
        <button @click=${this._resetDefaults}>Reset to Defaults</button>
        <input
          class="filter-input"
          type="text"
          placeholder="Filter actions..."
          .value=${this._filter}
          @input=${(e: InputEvent) => {
            this._filter = (e.target as HTMLInputElement).value;
          }}
        />
      </div>
      <shenas-data-list
        .columns=${[
          { key: "category", label: "Category", class: "muted" },
          { key: "label", label: "Action" },
          {
            key: "binding",
            label: "Binding",
            render: (row: Record<string, unknown>) => this._renderBindingCell((row as unknown as HotkeyAction).id),
          },
        ]}
        .rows=${filtered as unknown as Record<string, unknown>[]}
        .actions=${(row: Record<string, unknown>) => this._renderRowActions((row as unknown as HotkeyAction).id)}
        empty-text="No hotkey actions"
      ></shenas-data-list>
    `;
  }

  _renderBindingCell(actionId: string) {
    const binding = this._bindings[actionId] || "";
    const isRecording = this._recording === actionId;
    const conflictLabel = this._conflict ? this._getActionLabel(this._conflict) : "";
    if (isRecording) {
      return html`
        <span class="recording">${this._recordedKey || "Press a key..."}</span>
        ${this._conflict ? html`<span class="conflict">Conflicts with ${conflictLabel}</span>` : ""}
      `;
    }
    return binding ? html`<span class="kbd">${binding}</span>` : html`<span class="unbound">-</span>`;
  }

  _renderRowActions(actionId: string) {
    const binding = this._bindings[actionId] || "";
    const isRecording = this._recording === actionId;
    if (isRecording) {
      return html`
        <button @click=${this._applyRecording} ?disabled=${!this._recordedKey}>Save</button>
        <button @click=${this._stopRecording}>Cancel</button>
      `;
    }
    return html`
      <button class="edit-btn" @click=${() => this._startRecording(actionId)}>Edit</button>
      ${binding ? html`<button class="edit-btn" @click=${() => this._clearBinding(actionId)}>Clear</button>` : ""}
    `;
  }
}

customElements.define("shenas-hotkeys", HotkeysPage);
