import { LitElement, html, css } from "lit";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  renderMessage,
  buttonStyles,
  formStyles,
  messageStyles,
} from "shenas-frontends";
import { GET_PLUGIN_CONFIG } from "./graphql/queries.ts";
import { SET_CONFIG } from "./graphql/mutations.ts";
import { gqlTag as gql } from "shenas-frontends";

const GET_ENTITIES_BY_STATUS = gql`
  {
    entities(status: "enabled") {
      uuid
      type
      name
    }
  }
`;

interface ConfigEntry {
  key: string;
  label: string;
  value: string;
  description: string;
  uiWidget?: string;
  defaultValue?: string;
}

interface EntityOption {
  uuid: string;
  name: string;
  type: string;
}

interface PluginConfig {
  kind: string;
  name: string;
  entries: ConfigEntry[];
}

interface Message {
  type: string;
  text: string;
}

class ConfigPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    kind: { type: String },
    name: { type: String },
    entityTypes: { type: Array },
    _config: { state: true },
    _message: { state: true },
    _editing: { state: true },
    _editValue: { state: true },
    _freqNum: { state: true },
    _freqUnit: { state: true },
    _entityOptions: { state: true },
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

  static _UNIT_MULTIPLIERS: Record<string, number> = { seconds: 1 / 60, minutes: 1, hours: 60, days: 1440 };
  static _DURATION_FIELDS = new Set(["sync_frequency", "lookback_period"]);

  declare apiBase: string;
  declare kind: string;
  declare name: string;
  declare entityTypes: string[];
  declare _config: PluginConfig | null;
  declare _message: Message | null;
  declare _editing: string | null;
  declare _editValue: string;
  declare _freqNum: string;
  declare _freqUnit: string;
  declare _entityOptions: EntityOption[];

  private _configQuery = new ApolloQueryController(this, GET_PLUGIN_CONFIG, {
    client: getClient(),
    noAutoSubscribe: true,
  });

  private _setConfigMutation = new ApolloMutationController(this, SET_CONFIG, {
    client: getClient(),
  });

  get _loading(): boolean {
    return this._configQuery.loading;
  }

  constructor() {
    super();
    this.apiBase = "/api";
    this.kind = "";
    this.name = "";
    this.entityTypes = [];
    this._config = null;
    this._message = null;
    this._editing = null;
    this._editValue = "";
    this._freqNum = "";
    this._freqUnit = "hours";
    this._entityOptions = [];
  }

  willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("kind") || changed.has("name")) {
      this._fetchConfig();
    }
  }

  async _fetchConfig(): Promise<void> {
    if (!this.kind || !this.name) return;
    const result = await this._configQuery.client!.query({
      query: GET_PLUGIN_CONFIG,
      variables: { kind: this.kind, name: this.name },
      fetchPolicy: "network-only",
    });
    const entries = (result.data?.pluginConfig as ConfigEntry[]) || [];
    this._config = entries.length > 0 ? { kind: this.kind, name: this.name, entries } : null;
    // Fetch entities if any config entry uses the entity_picker widget.
    if (entries.some((entry) => entry.uiWidget === "entity_picker") && this.entityTypes.length > 0) {
      await this._fetchEntities();
    }
    this.requestUpdate();
  }

  private _client = getClient();

  async _fetchEntities(): Promise<void> {
    const { data } = await this._client.query({ query: GET_ENTITIES_BY_STATUS, fetchPolicy: "network-only" });
    const all = (data?.entities || []) as EntityOption[];
    const typeSet = new Set(this.entityTypes);
    this._entityOptions = all.filter((entity) => typeSet.has(entity.type));
  }

  _startEdit(key: string, currentValue: string): void {
    this._editing = key;
    this._editValue = currentValue || "";
    if (ConfigPage._DURATION_FIELDS.has(key) && currentValue) {
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
    } else if (ConfigPage._DURATION_FIELDS.has(key)) {
      this._freqNum = "";
      this._freqUnit = "hours";
    }
  }

  _cancelEdit(): void {
    this._editing = null;
    this._editValue = "";
  }

  _freqToMinutes(): string | null {
    const num = parseFloat(this._freqNum);
    if (isNaN(num) || num <= 0) return null;
    return String(Math.round(num * ConfigPage._UNIT_MULTIPLIERS[this._freqUnit]));
  }

  _formatFreq(minutes: string): string {
    const m = parseFloat(minutes);
    if (isNaN(m)) return minutes;
    if (m >= 1440 && m % 1440 === 0) return `${m / 1440} day${m / 1440 !== 1 ? "s" : ""}`;
    if (m >= 60 && m % 60 === 0) return `${m / 60} hour${m / 60 !== 1 ? "s" : ""}`;
    if (m >= 1) return `${m} minute${m !== 1 ? "s" : ""}`;
    return `${m * 60} second${m * 60 !== 1 ? "s" : ""}`;
  }

  async _saveEdit(key: string): Promise<void> {
    const value = ConfigPage._DURATION_FIELDS.has(key) ? this._freqToMinutes() : this._editValue;
    if (ConfigPage._DURATION_FIELDS.has(key) && value === null) {
      this._message = { type: "error", text: "Enter a positive number" };
      return;
    }
    try {
      const result = await this._setConfigMutation.mutate({
        variables: { kind: this.kind, name: this.name, key, value },
      });
      const ok = (result.data?.setConfig as Record<string, unknown> | undefined)?.ok;
      if (ok) {
        this._message = { type: "success", text: `Updated ${key}` };
        this._editing = null;
        await this._fetchConfig();
      } else {
        this._message = { type: "error", text: "Update failed" };
      }
    } catch (e) {
      this._message = { type: "error", text: (e as Error).message || "Update failed" };
    }
  }

  render() {
    const empty = !this._config || this._config.entries.length === 0;
    return html`
      <shenas-page
        ?loading=${this._loading}
        ?empty=${empty}
        loading-text="Loading config..."
        empty-text="No configuration settings for this plugin."
      >
        ${renderMessage(this._message)} ${this._config?.entries.map((e) => this._renderEntry(e))}
      </shenas-page>
    `;
  }

  _renderFreqEdit(entry: ConfigEntry) {
    return html` <div class="edit-row">
      <input
        class="config-input"
        type="number"
        min="0"
        step="any"
        style="width: 80px"
        .value=${this._freqNum}
        @input=${(ev: InputEvent) => {
          this._freqNum = (ev.target as HTMLInputElement).value;
        }}
        @keydown=${(ev: KeyboardEvent) => {
          if (ev.key === "Enter") this._saveEdit(entry.key);
          if (ev.key === "Escape") this._cancelEdit();
        }}
      />
      <select
        @change=${(ev: Event) => {
          this._freqUnit = (ev.target as HTMLSelectElement).value;
        }}
      >
        ${Object.keys(ConfigPage._UNIT_MULTIPLIERS).map(
          (u) => html` <option value=${u} ?selected=${this._freqUnit === u}>${u}</option> `,
        )}
      </select>
      <button @click=${() => this._saveEdit(entry.key)}>Save</button>
      <button @click=${this._cancelEdit}>Cancel</button>
    </div>`;
  }

  _renderEntityPicker(entry: ConfigEntry) {
    const selected = entry.value
      ? entry.value
          .split(",")
          .map((uuid) => uuid.trim())
          .filter(Boolean)
      : [];
    const options = this._entityOptions.map((entity) => ({ value: entity.uuid, label: entity.name }));
    return html`
      <div class="config-detail">
        <shenas-multi-select
          label=""
          .options=${options}
          .value=${selected}
          @change=${async (event: CustomEvent) => {
            const uuids = (event.detail.value as string[]).join(",");
            try {
              await this._setConfigMutation.mutate({
                variables: { kind: this.kind, name: this.name, key: entry.key, value: uuids || null },
              });
              await this._fetchConfig();
            } catch (error) {
              this._message = { type: "error", text: (error as Error).message };
            }
          }}
        ></shenas-multi-select>
        ${entry.description ? html`<div class="config-desc">${entry.description}</div>` : ""}
      </div>
    `;
  }

  _renderEntry(entry: ConfigEntry) {
    if (entry.uiWidget === "entity_picker") {
      return html`
        <div class="config-row">
          <div class="config-key">${entry.label || entry.key}</div>
          ${this._renderEntityPicker(entry)}
        </div>
      `;
    }
    const isEditing = this._editing === entry.key;
    const isFreq = ConfigPage._DURATION_FIELDS.has(entry.key);
    const displayValue = isFreq && entry.value ? this._formatFreq(entry.value) : entry.value;
    return html`
      <div class="config-row">
        <div class="config-key">${entry.label || entry.key}</div>
        ${isEditing
          ? isFreq
            ? this._renderFreqEdit(entry)
            : html` <div class="edit-row">
                <input
                  class="config-input"
                  .value=${this._editValue}
                  @input=${(ev: InputEvent) => {
                    this._editValue = (ev.target as HTMLInputElement).value;
                  }}
                  @keydown=${(ev: KeyboardEvent) => {
                    if (ev.key === "Enter") this._saveEdit(entry.key);
                    if (ev.key === "Escape") this._cancelEdit();
                  }}
                />
                <button @click=${() => this._saveEdit(entry.key)}>Save</button>
                <button @click=${this._cancelEdit}>Cancel</button>
              </div>`
          : html` <div class="config-detail">
              <div
                class="config-value ${displayValue ? "" : "empty"}"
                @click=${() => this._startEdit(entry.key, entry.value)}
                style="cursor: pointer"
                title="Click to edit"
              >
                ${displayValue || (entry.defaultValue ? `${entry.defaultValue} (default)` : "not set")}
              </div>
              ${entry.description ? html`<div class="config-desc">${entry.description}</div>` : ""}
            </div>`}
      </div>
    `;
  }
}

customElements.define("shenas-config", ConfigPage);
