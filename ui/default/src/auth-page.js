import { LitElement, html, css } from "lit";
import { apiFetch, apiFetchFull, renderMessage } from "./api.js";
import { buttonStyles, formStyles, messageStyles, utilityStyles } from "./shared-styles.js";

class AuthPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    pipeName: { type: String, attribute: "pipe-name" },
    _fields: { state: true },
    _instructions: { state: true },
    _loading: { state: true },
    _message: { state: true },
    _needsMfa: { state: true },
    _oauthUrl: { state: true },
    _submitting: { state: true },
  };

  static styles = [
    buttonStyles,
    formStyles,
    messageStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .instructions {
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        line-height: 1.6;
        margin-bottom: 1rem;
        white-space: pre-line;
      }
      .oauth-link {
        display: inline-block;
        margin-top: 0.5rem;
        color: var(--shenas-primary, #0066cc);
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this.pipeName = "";
    this._fields = [];
    this._instructions = "";
    this._loading = true;
    this._message = null;
    this._needsMfa = false;
    this._oauthUrl = null;
    this._submitting = false;
  }

  willUpdate(changed) {
    if (changed.has("pipeName")) {
      this._fetchFields();
    }
  }

  async _fetchFields() {
    if (!this.pipeName) return;
    this._loading = true;
    this._needsMfa = false;
    this._oauthUrl = null;
    const data = await apiFetch(this.apiBase, `/auth/${this.pipeName}/fields`);
    if (data) {
      this._fields = data.fields || [];
      this._instructions = data.instructions || "";
    }
    this._loading = false;
  }

  async _submit() {
    this._submitting = true;
    this._message = null;
    const credentials = {};

    if (this._needsMfa) {
      const input = this.renderRoot.querySelector("#mfa-code");
      credentials.mfa_code = input?.value?.trim() || "";
    } else if (this._oauthUrl) {
      credentials.auth_complete = "true";
    } else {
      for (const field of this._fields) {
        const input = this.renderRoot.querySelector(`#field-${field.name}`);
        const val = input?.value?.trim();
        if (val) credentials[field.name] = val;
      }
    }

    const { data } = await apiFetchFull(this.apiBase, `/auth/${this.pipeName}`, {
      method: "POST",
      json: { credentials },
    });
    this._submitting = false;

    if (data.ok) {
      this._message = { type: "success", text: data.message };
      this._needsMfa = false;
      this._oauthUrl = null;
    } else if (data.needs_mfa) {
      this._needsMfa = true;
      this._message = { type: "success", text: "MFA code required" };
    } else if (data.oauth_url) {
      this._oauthUrl = data.oauth_url;
      this._message = { type: "success", text: data.message };
    } else {
      this._message = { type: "error", text: data.error || "Authentication failed" };
      this._needsMfa = false;
      this._oauthUrl = null;
    }
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading auth...</p>`;
    }
    if (this._fields.length === 0 && !this._instructions) {
      return html`<p class="empty">No authentication required for this plugin.</p>`;
    }

    return html`
      ${renderMessage(this._message)}
      ${this._instructions
        ? html`<div class="instructions">${this._instructions}</div>`
        : ""}
      ${this._oauthUrl ? this._renderOAuth()
        : this._needsMfa ? this._renderMfa()
        : this._renderFields()}
    `;
  }

  _renderFields() {
    return html`
      ${this._fields.map((f) => html`
        <div class="field">
          <label for="field-${f.name}">${f.prompt}</label>
          <input id="field-${f.name}"
            type="${f.hide ? "password" : "text"}"
            @keydown=${(e) => { if (e.key === "Enter") this._submit(); }}
          />
        </div>
      `)}
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting ? "Authenticating..." : "Authenticate"}
        </button>
      </div>
    `;
  }

  _renderMfa() {
    return html`
      <div class="field">
        <label for="mfa-code">MFA Code</label>
        <input id="mfa-code" type="text" autocomplete="one-time-code"
          @keydown=${(e) => { if (e.key === "Enter") this._submit(); }}
        />
      </div>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting ? "Verifying..." : "Verify"}
        </button>
      </div>
    `;
  }

  _renderOAuth() {
    return html`
      <p>
        <a class="oauth-link" href="${this._oauthUrl}" target="_blank" rel="noopener">
          Open authorization page
        </a>
      </p>
      <p style="font-size:0.85rem;color:var(--shenas-text-secondary, #666)">
        After authorizing in your browser, click Complete below.
      </p>
      <div class="actions">
        <button @click=${this._submit} ?disabled=${this._submitting}>
          ${this._submitting ? "Completing..." : "Complete"}
        </button>
      </div>
    `;
  }
}

customElements.define("shenas-auth", AuthPage);
