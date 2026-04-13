import { LitElement, html, css } from "lit";
import { gql, gqlFull, renderMessage, buttonStyles, formStyles, messageStyles } from "shenas-frontends";

interface AuthField {
  name: string;
  prompt: string;
  hide: boolean;
}

interface Message {
  type: string;
  text: string;
}

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

  declare apiBase: string;
  declare pipeName: string;
  declare _fields: AuthField[];
  declare _instructions: string;
  declare _loading: boolean;
  declare _message: Message | null;
  declare _needsMfa: boolean;
  declare _oauthUrl: string | null;
  declare _submitting: boolean;
  declare _stored: string[];

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

  willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("pipeName")) {
      this._fetchFields();
    }
  }

  async _fetchFields(): Promise<void> {
    if (!this.pipeName) return;
    this._loading = true;
    this._needsMfa = false;
    this._oauthUrl = null;
    const data = await gql(
      this.apiBase,
      `query($pipe: String!) { authFields(pipe: $pipe) { fields { name prompt hide } instructions stored } }`,
      { pipe: this.pipeName },
    );
    if (data?.authFields) {
      const authFields = data.authFields as Record<string, unknown>;
      this._fields = (authFields.fields as AuthField[]) || [];
      this._instructions = (authFields.instructions as string) || "";
      this._stored = (authFields.stored as string[]) || [];
    }
    this._loading = false;
  }

  async _submit(): Promise<void> {
    this._submitting = true;
    this._message = null;
    const credentials: Record<string, string> = {};

    if (this._needsMfa) {
      const input = this.renderRoot.querySelector("#mfa-code") as HTMLInputElement | null;
      credentials.mfa_code = input?.value?.trim() || "";
    } else if (this._oauthUrl) {
      credentials.auth_complete = "true";
    } else {
      for (const field of this._fields) {
        const input = this.renderRoot.querySelector(`#field-${field.name}`) as HTMLInputElement | null;
        const val = input?.value?.trim();
        if (val) credentials[field.name] = val;
      }
    }

    const { data } = await gqlFull(
      this.apiBase,
      `mutation($pipe: String!, $creds: JSON!) { authenticate(pipe: $pipe, credentials: $creds) { ok message error needsMfa oauthUrl oauthRedirect } }`,
      { pipe: this.pipeName, creds: credentials },
    );
    this._submitting = false;
    const auth = data?.authenticate as Record<string, unknown> | undefined;

    if (auth?.oauthRedirect) {
      // Server-side redirect flow: navigate directly to the provider
      window.location.href = auth.oauthRedirect as string;
      return;
    }
    if (auth?.ok) {
      this._message = { type: "success", text: auth.message as string };
      this._needsMfa = false;
      this._oauthUrl = null;
      this._fetchFields();
    } else if (auth?.needsMfa) {
      this._needsMfa = true;
      this._message = { type: "success", text: "MFA code required" };
    } else if (auth?.oauthUrl) {
      // Legacy flow (non-redirect OAuth sources)
      this._oauthUrl = auth.oauthUrl as string;
      this._message = { type: "success", text: auth.message as string };
    } else {
      this._message = { type: "error", text: (auth?.error as string) || "Authentication failed" };
      this._needsMfa = false;
      this._oauthUrl = null;
    }
  }

  render() {
    const empty = this._fields.length === 0 && !this._instructions;
    return html`
      <shenas-page
        ?loading=${this._loading}
        ?empty=${empty}
        loading-text="Loading auth..."
        empty-text="No authentication required for this plugin."
      >
        ${renderMessage(this._message)}
        ${this._stored.length > 0
          ? html`<div class="stored-creds">
              ${this._stored.map((s) => html`<div class="stored-item">&#10003; ${s} configured</div>`)}
            </div>`
          : ""}
        ${this._instructions
          ? html`<div class="instructions">${this._renderInstructions(this._instructions)}</div>`
          : ""}
        ${this._oauthUrl ? this._renderOAuth() : this._needsMfa ? this._renderMfa() : this._renderFields()}
      </shenas-page>
    `;
  }

  _renderInstructions(text: string) {
    // Auto-linkify URLs in plain-text instructions. Splits on http(s):// URLs
    // and renders them as <a target="_blank">; everything else stays as text
    // (Lit auto-escapes), so the white-space: pre-line still produces line breaks.
    const parts: (string | ReturnType<typeof html>)[] = [];
    const re = /(https?:\/\/[^\s)<>]+[^\s)<>.,;:!?])/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parts.push(text.slice(last, m.index));
      parts.push(html`<a href=${m[0]} target="_blank" rel="noopener noreferrer">${m[0]}</a>`);
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push(text.slice(last));
    return parts;
  }

  _renderFields() {
    return html`
      ${this._fields.map(
        (f) => html`
          <div class="field">
            <label for="field-${f.name}">${f.prompt}</label>
            <input
              id="field-${f.name}"
              type="${f.hide ? "password" : "text"}"
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === "Enter") this._submit();
              }}
            />
          </div>
        `,
      )}
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
        <input
          id="mfa-code"
          type="text"
          autocomplete="one-time-code"
          @keydown=${(e: KeyboardEvent) => {
            if (e.key === "Enter") this._submit();
          }}
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
        <a class="oauth-link" href="${this._oauthUrl}" target="_blank" rel="noopener"> Open authorization page </a>
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
