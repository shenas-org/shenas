import { LitElement, html, css } from "lit";
import {
  gql,
  gqlFull,
  registerCommands,
  renderMessage,
  buttonStyles,
  linkStyles,
  messageStyles,
} from "shenas-frontends";

interface SettingsNavItem {
  id: string;
  label: string;
}

export const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { id: "profile", label: "Profile" },
  { id: "categories", label: "Categories" },
  { id: "hotkeys", label: "Hotkeys" },
];

interface SettingCategory {
  id: string;
  name: string;
  description?: string;
  settings: Setting[];
}

interface Setting {
  id: string;
  key: string;
  display_name: string;
  value: unknown;
  type: "string" | "number" | "boolean" | "select";
  description?: string;
  options?: { label: string; value: unknown }[];
  required?: boolean;
  default?: unknown;
}

interface SettingsData {
  categories: SettingCategory[];
  [key: string]: unknown;
}

class SettingsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _settings: { state: true },
    _categories: { state: true },
    _loading: { state: true },
    _saving: { state: true },
    _message: { state: true },
    _expandedCategories: { state: true },
    _changedSettings: { state: true },
  };

  static styles = [
    buttonStyles,
    linkStyles,
    messageStyles,
    css`
      :host {
        display: block;
        color: var(--text-color);
        background: var(--bg-color);
      }

      .container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1rem;
      }

      .page-header {
        margin-bottom: 2rem;
      }

      .page-title {
        font-size: 1.875rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
      }

      .page-description {
        color: var(--text-secondary);
        font-size: 0.95rem;
      }

      .settings-grid {
        display: grid;
        gap: 1rem;
      }

      .category {
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        overflow: hidden;
      }

      .category-header {
        padding: 1rem;
        background: var(--bg-secondary);
        border-bottom: 1px solid var(--border-color);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        user-select: none;
      }

      .category-header:hover {
        background: var(--bg-tertiary);
      }

      .category-header.expanded {
        border-bottom-color: var(--accent-color);
      }

      .category-title {
        font-size: 1.1rem;
        font-weight: 500;
      }

      .category-description {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
      }

      .category-toggle {
        font-size: 1.25rem;
        transition: transform 0.2s ease;
      }

      .category-toggle.expanded {
        transform: rotate(180deg);
      }

      .category-content {
        display: none;
        padding: 1rem;
        background: var(--bg-color);
      }

      .category-content.expanded {
        display: block;
        animation: slideDown 0.2s ease;
      }

      @keyframes slideDown {
        from {
          opacity: 0;
          max-height: 0;
        }
        to {
          opacity: 1;
          max-height: 1000px;
        }
      }

      .settings-form {
        display: grid;
        gap: 1.5rem;
      }

      .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }

      .form-label {
        font-weight: 500;
        font-size: 0.95rem;
      }

      .form-label.required::after {
        content: " *";
        color: #ef4444;
      }

      .form-input,
      .form-select {
        padding: 0.5rem;
        border: 1px solid var(--border-color);
        border-radius: 0.375rem;
        font-size: 0.95rem;
        background: var(--bg-color);
        color: var(--text-color);
        font-family: inherit;
      }

      .form-input:focus,
      .form-select:focus {
        outline: none;
        border-color: var(--accent-color);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
      }

      .form-input:disabled,
      .form-select:disabled {
        background: var(--bg-secondary);
        color: var(--text-secondary);
        cursor: not-allowed;
      }

      .form-checkbox {
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }

      .form-checkbox input {
        cursor: pointer;
      }

      .form-help {
        font-size: 0.85rem;
        color: var(--text-secondary);
      }

      .form-error {
        font-size: 0.85rem;
        color: #ef4444;
      }

      .action-bar {
        position: sticky;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem;
        background: var(--bg-color);
        border-top: 1px solid var(--border-color);
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        z-index: 10;
      }

      .empty-state {
        padding: 2rem;
        text-align: center;
        color: var(--text-secondary);
      }

      .unsaved-indicator {
        position: fixed;
        top: 1rem;
        right: 1rem;
        padding: 0.75rem 1rem;
        background: #f59e0b;
        color: white;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        z-index: 20;
      }
    `,
  ];

  declare apiBase: string;
  declare _settings: Record<string, unknown>;
  declare _categories: SettingCategory[];
  declare _loading: boolean;
  declare _saving: boolean;
  declare _message: { type: string; text: string } | null;
  declare _expandedCategories: Set<string>;
  declare _changedSettings: Map<string, unknown>;

  constructor() {
    super();
    this.apiBase = "http://localhost:3000";
    this._settings = {};
    this._categories = [];
    this._loading = false;
    this._saving = false;
    this._message = null;
    this._expandedCategories = new Set();
    this._changedSettings = new Map();
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadSettings();
    registerCommands(this, "settings-page", [
      { command: "save", action: () => this._saveSettings() },
      { command: "reset", action: () => this._resetSettings() },
    ]);
  }

  private async _loadSettings() {
    this._loading = true;
    try {
      const query = `
        query {
          settings {
            categories {
              id
              name
              description
              settings {
                id
                key
                display_name
                value
                type
                description
                options {
                  label
                  value
                }
                required
                default
              }
            }
          }
        }
      `;

      const response = (await gql(`${this.apiBase}/api/graphql`, query)) as Record<string, unknown> | null;
      const data = response as { settings?: SettingsData } | null;

      if (data?.settings) {
        const settingsData: SettingsData = data.settings;
        this._categories = settingsData.categories || [];

        // Initialize expanded state - expand first category by default
        if (this._categories.length > 0) {
          this._expandedCategories.add(this._categories[0].id);
        }

        // Copy initial settings values
        this._settings = {};
        for (const category of this._categories) {
          for (const setting of category.settings) {
            this._settings[setting.id] = setting.value;
          }
        }
      }
    } catch (error) {
      this._message = {
        type: "error",
        text: `Failed to load settings: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      this._loading = false;
    }
  }

  private async _saveSettings() {
    if (this._changedSettings.size === 0) {
      this._message = {
        type: "info",
        text: "No changes to save",
      };
      return;
    }

    this._saving = true;
    try {
      const updates = Array.from(this._changedSettings.entries()).map(([id, value]) => ({
        id,
        value,
      }));

      const response = await gqlFull(
        `${this.apiBase}/api/graphql`,
        `mutation UpdateSettings($updates: [SettingUpdate!]!) {
          updateSettings(updates: $updates) {
            success
            message
          }
        }`,
        { updates },
      );

      const result = response as { data?: { updateSettings?: { success: boolean; message?: string } } };
      if (result.data?.updateSettings?.success) {
        this._message = {
          type: "success",
          text: result.data.updateSettings.message || "Settings saved successfully",
        };
        this._changedSettings.clear();
        this._loadSettings();
      } else {
        this._message = {
          type: "error",
          text: result.data?.updateSettings?.message || "Failed to save settings",
        };
      }
    } catch (error) {
      this._message = {
        type: "error",
        text: `Failed to save settings: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      this._saving = false;
    }
  }

  private _resetSettings() {
    this._changedSettings.clear();
    this._loadSettings();
    this._message = {
      type: "info",
      text: "Settings reset to last saved state",
    };
  }

  private _toggleCategory(categoryId: string) {
    if (this._expandedCategories.has(categoryId)) {
      this._expandedCategories.delete(categoryId);
    } else {
      this._expandedCategories.add(categoryId);
    }
    this.requestUpdate();
  }

  private _updateSetting(settingId: string, value: unknown) {
    this._settings[settingId] = value;
    this._changedSettings.set(settingId, value);
    this.requestUpdate();
  }

  private _renderSettingInput(setting: Setting) {
    const value = this._settings[setting.id];

    switch (setting.type) {
      case "boolean":
        return html`
          <div class="form-checkbox">
            <input
              type="checkbox"
              id="setting-${setting.id}"
              ?checked=${value}
              @change=${(e: Event) => this._updateSetting(setting.id, (e.target as HTMLInputElement).checked)}
            />
            <label for="setting-${setting.id}">${setting.display_name}</label>
          </div>
        `;

      case "select":
        return html`
          <select
            id="setting-${setting.id}"
            class="form-select"
            .value=${String(value)}
            @change=${(e: Event) => this._updateSetting(setting.id, (e.target as HTMLInputElement).value)}
          >
            ${setting.options?.map(
              (opt) => html` <option value=${opt.value} ?selected=${value === opt.value}>${opt.label}</option> `,
            )}
          </select>
        `;

      case "number":
        return html`
          <input
            type="number"
            id="setting-${setting.id}"
            class="form-input"
            .value=${String(value || "")}
            ?required=${setting.required}
            @change=${(e: Event) => this._updateSetting(setting.id, Number((e.target as HTMLInputElement).value))}
          />
        `;

      case "string":
      default:
        return html`
          <input
            type="text"
            id="setting-${setting.id}"
            class="form-input"
            .value=${String(value || "")}
            ?required=${setting.required}
            @change=${(e: Event) => this._updateSetting(setting.id, (e.target as HTMLInputElement).value)}
          />
        `;
    }
  }

  render() {
    if (this._loading) {
      return html`
        <div class="container">
          <div class="empty-state">Loading settings...</div>
        </div>
      `;
    }

    return html`
      <div class="container">
        ${this._message ? renderMessage(this._message) : ""}
        ${this._changedSettings.size > 0 ? html`<div class="unsaved-indicator">You have unsaved changes</div>` : ""}

        <div class="page-header">
          <h1 class="page-title">Settings</h1>
          <p class="page-description">Configure application preferences and options</p>
        </div>

        ${this._categories.length === 0
          ? html`<div class="empty-state">No settings available</div>`
          : html`
              <div class="settings-grid">
                ${this._categories.map(
                  (category) => html`
                    <div class="category">
                      <div
                        class="category-header ${this._expandedCategories.has(category.id) ? "expanded" : ""}"
                        @click=${() => this._toggleCategory(category.id)}
                      >
                        <div>
                          <div class="category-title">${category.name}</div>
                          ${category.description
                            ? html`<div class="category-description">${category.description}</div>`
                            : ""}
                        </div>
                        <div class="category-toggle ${this._expandedCategories.has(category.id) ? "expanded" : ""}">
                          ▼
                        </div>
                      </div>
                      <div class="category-content ${this._expandedCategories.has(category.id) ? "expanded" : ""}">
                        <form class="settings-form">
                          ${category.settings.map(
                            (setting) => html`
                              <div class="form-group">
                                ${setting.type !== "boolean"
                                  ? html`
                                      <label
                                        for="setting-${setting.id}"
                                        class="form-label ${setting.required ? "required" : ""}"
                                      >
                                        ${setting.display_name}
                                      </label>
                                    `
                                  : ""}
                                ${this._renderSettingInput(setting)}
                                ${setting.description ? html`<p class="form-help">${setting.description}</p>` : ""}
                              </div>
                            `,
                          )}
                        </form>
                      </div>
                    </div>
                  `,
                )}
              </div>
            `}
        ${this._categories.length > 0
          ? html`
              <div class="action-bar">
                <button
                  @click=${() => this._resetSettings()}
                  ?disabled=${this._changedSettings.size === 0 || this._saving}
                  class="btn-secondary"
                >
                  Reset
                </button>
                <button
                  @click=${() => this._saveSettings()}
                  ?disabled=${this._changedSettings.size === 0 || this._saving}
                  class="btn-primary"
                >
                  ${this._saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            `
          : ""}
      </div>
    `;
  }
}

customElements.define("shenas-settings", SettingsPage);
export { SettingsPage };
