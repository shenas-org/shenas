import { LitElement, html, css } from 'lit';
import { query } from 'lit/decorators.js';
import type { TemplateResult, CSSResult } from 'lit';

interface ConfigValue {
  key: string;
  value: string;
  description?: string;
}

export class ConfigPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: 'api-base' },
    _configs: { state: true },
    _error: { state: true },
    _loading: { state: true },
    _editingKey: { state: true },
  };

  declare apiBase: string;
  declare _configs: ConfigValue[];
  declare _error: string | null;
  declare _loading: boolean;
  declare _editingKey: string | null;

  @query('#config-value')
  declare configValueInput: HTMLInputElement;

  static styles: CSSResult = css`
    :host {
      display: block;
      font-family: var(--shenas-font, system-ui, sans-serif);
      color: var(--shenas-text, #e8e8ef);
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2rem;
    }

    h1 {
      margin: 0;
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--shenas-text-bright, #ffffff);
    }

    .controls {
      display: flex;
      gap: 0.5rem;
    }

    .controls button {
      background: var(--shenas-accent, #6c5ce7);
      border: none;
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 600;
      transition: opacity 0.2s;
    }

    .controls button:hover {
      opacity: 0.9;
    }

    .controls button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .config-list {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 8px;
      overflow: hidden;
    }

    .config-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .config-item:last-child {
      border-bottom: none;
    }

    .config-item.editing {
      background: var(--shenas-surface-alt, #2a2a3a);
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
    }

    .config-key {
      font-weight: 600;
      color: var(--shenas-text-bright, #ffffff);
    }

    .config-value {
      color: var(--shenas-text-muted, #a8a8c0);
      font-family: monospace;
      font-size: 0.9rem;
      word-break: break-all;
    }

    .config-description {
      color: var(--shenas-text-muted, #a8a8c0);
      font-size: 0.85rem;
      margin-top: 0.25rem;
    }

    .config-actions {
      display: flex;
      gap: 0.5rem;
    }

    .config-actions button {
      background: var(--shenas-surface-alt, #2a2a3a);
      border: 1px solid var(--shenas-border, #2a2a3a);
      color: var(--shenas-text, #e8e8ef);
      padding: 0.4rem 0.8rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.2s;
    }

    .config-actions button:hover {
      background: var(--shenas-accent, #6c5ce7);
      border-color: var(--shenas-accent, #6c5ce7);
    }

    .edit-form {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    label {
      color: var(--shenas-text, #e8e8ef);
      font-size: 0.9rem;
      font-weight: 500;
    }

    input {
      padding: 0.5rem;
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 4px;
      color: var(--shenas-text, #e8e8ef);
      font-family: monospace;
      font-size: 0.9rem;
    }

    input:focus {
      outline: none;
      border-color: var(--shenas-accent, #6c5ce7);
    }

    .error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;
      padding: 1rem;
      border-radius: 6px;
      margin-bottom: 1rem;
    }

    .loading {
      text-align: center;
      padding: 2rem;
      color: var(--shenas-text-muted, #a8a8c0);
    }
  `;

  constructor() {
    super();
    this.apiBase = '';
    this._configs = [];
    this._error = null;
    this._loading = false;
    this._editingKey = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this.loadConfigs();
  }

  private async loadConfigs() {
    this._loading = true;
    this._error = null;

    try {
      const response = await fetch(`${this.apiBase}/api/config`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load configuration');
      }

      const data = await response.json();
      this._configs = data.configs || [];
    } catch (error) {
      this._error = error instanceof Error ? error.message : String(error);
    } finally {
      this._loading = false;
    }
  }

  private startEdit(key: string) {
    this._editingKey = key;
  }

  private cancelEdit() {
    this._editingKey = null;
  }

  private async saveEdit(event: Event) {
    event.preventDefault();
    const value = this.configValueInput.value;

    if (!this._editingKey || !value) {
      return;
    }

    this._loading = true;
    this._error = null;

    try {
      const response = await fetch(
        `${this.apiBase}/api/config/${this._editingKey}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: JSON.stringify({ value }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to update configuration');
      }

      await this.loadConfigs();
      this._editingKey = null;
    } catch (error) {
      this._error = error instanceof Error ? error.message : String(error);
    } finally {
      this._loading = false;
    }
  }

  render(): TemplateResult {
    return html`
      <div class="container">
        <div class="header">
          <h1>Configuration</h1>
          <div class="controls">
            <button @click=${this.loadConfigs.bind(this)}
              ?disabled=${this._loading}>
              Refresh
            </button>
          </div>
        </div>

        ${this._error ? html`<div class="error">${this._error}</div>` : ''}

        ${this._loading && this._configs.length === 0
          ? html`<div class="loading">Loading configuration...</div>`
          : html`
              <div class="config-list">
                ${this._configs.map((config) =>
                  this._editingKey === config.key
                    ? html`
                        <div class="config-item editing">
                          <div>
                            <div class="config-key">${config.key}</div>
                            ${config.description
                              ? html`<div class="config-description">
                                  ${config.description}
                                </div>`
                              : ''}
                          </div>
                          <form
                            @submit=${this.saveEdit.bind(this)}
                            class="edit-form"
                          >
                            <div class="form-group">
                              <label for="config-value">Value</label>
                              <input
                                id="config-value"
                                type="text"
                                .value=${config.value}
                                required
                              />
                            </div>
                            <div class="config-actions">
                              <button
                                type="submit"
                                ?disabled=${this._loading}
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                @click=${this.cancelEdit.bind(this)}
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                        </div>
                      `
                    : html`
                        <div class="config-item">
                          <div>
                            <div class="config-key">${config.key}</div>
                            <div class="config-value">${config.value}</div>
                            ${config.description
                              ? html`<div class="config-description">
                                  ${config.description}
                                </div>`
                              : ''}
                          </div>
                          <div class="config-actions">
                            <button
                              @click=${() => this.startEdit(config.key)}
                            >
                              Edit
                            </button>
                          </div>
                        </div>
                      `
                )}
              </div>
            `}
      </div>
    `;
  }
}

customElements.define('shenas-config-page', ConfigPage);
