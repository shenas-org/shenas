import { LitElement, html, css } from "lit";
import { gql, gqlFull, renderMessage } from "./api.js";
import { buttonStyles, formStyles, messageStyles } from "./shared-styles.js";

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
    _stored: { state: true },
  };

  static styles = [
    buttonStyles,
    formStyles,
    messageStyles,
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
      .stored-creds {
        margin-bottom: 1rem;
        padding: 0.6rem 0.8rem;
        background: var(--shenas-success-bg, #e8f5e9);
        border-radius: 4px;
        font-size: 0.85rem;
        color: var(--shenas-success, #2e7d32);
      }
      .stored-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.15rem 0;
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
    this._stored = [];
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
    const data = await gql(this.apiBase, `query($pipe: String!) { authFields(pipe: $pipe) { fields { name prompt hide } instructions stored } }`, { pipe: this.pipeName });
    if (data?.authFields) {
      this._fields = data.authFields.fields || [];
      this._instructions = data.authFields.instructions || "";
      this._stored = data.authFields.stored || [];
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

    const { data } = await gqlFull(this.apiBase, `mutation($pipe: String!, $creds: JSON!) { authenticate(pipe: $pipe, credentials: $creds) { ok message error needsMfa oauthUrl } }`, { pipe: this.pipeName, creds: credentials });
    this._submitting = false;
    const auth = data?.authenticate;

    if (auth?.ok) {
      this._message = { type: "success", text: auth.message };
      this._needsMfa = false;
      this._oauthUrl = null;
      this._fetchFields();
    } else if (auth?.needsMfa) {
      this._needsMfa = true;
      this._message = { type: "success", text: "MFA code required" };
    } else if (auth?.oauthUrl) {
      this._oauthUrl = auth.oauthUrl;
      this._message = { type: "success", text: auth.message };
    } else {
      this._message = { type: "error", text: auth?.error || "Authentication failed" };
      this._needsMfa = false;
      this._oauthUrl = null;
    }
  }

  render() {
    const empty = this._fields.length === 0 && !this._instructions;
    return html`
      <shenas-page ?loading=${this._loading} ?empty=${empty}
        loading-text="Loading auth..." empty-text="No authentication required for this plugin.">
        ${renderMessage(this._message)}
        ${this._stored.length > 0
          ? html`<div class="stored-creds">
              ${this._stored.map((s) => html`<div class="stored-item">&#10003; ${s} configured</div>`)}
            </div>`
          : ""}
        ${this._instructions
          ? html`<div class="instructions">${this._instructions}</div>`
          : ""}
        ${this._oauthUrl ? this._renderOAuth()
          : this._needsMfa ? this._renderMfa()
          : this._renderFields()}
      </shenas-page>
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
