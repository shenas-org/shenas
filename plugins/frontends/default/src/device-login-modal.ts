import { LitElement, html, css } from "lit";
import { buttonStyles, messageStyles, openExternal } from "shenas-frontends";

interface LoginPayload {
  authorization_url: string;
  state: string;
  error?: string;
}

interface StatusPayload {
  status: "pending" | "authorized" | "error" | "expired";
  error?: string;
}

type Phase = "loading" | "waiting" | "error";

/**
 * Modal for the OAuth 2.0 authorization-code + PKCE sign-in flow (RFC 8252).
 *
 * Lifecycle:
 *   1. On connectedCallback, calls GET <apiBase>/auth/login. The server
 *      generates a PKCE pair and a `state` handle, returns the authorization
 *      URL the user should open.
 *   2. The URL opens in the system browser via openExternal(); Kanidm
 *      redirects to the loopback /callback route once the user signs in.
 *   3. Meanwhile this component polls GET <apiBase>/auth/status?state=...
 *      every 2 s until the server reports `authorized` or `error`.
 *
 * Dispatches:
 *   @auth-changed  (bubbles, composed) — on successful authorization so parent
 *                  components (e.g. shenas-app) can refresh remote-user state.
 *   @device-login-cancel  (bubbles, composed) — when the user cancels.
 */
class ShenasDeviceLoginModal extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _phase: { state: true },
    _errorMessage: { state: true },
  };

  static styles = [
    buttonStyles,
    messageStyles,
    css`
      :host {
        display: block;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .dialog {
        background: var(--shenas-bg, #faf8f5);
        border: 1px solid var(--shenas-border, #d8d4cc);
        border-radius: 10px;
        padding: 2rem;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.16);
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
      }
      h2 {
        margin: 0;
        font-size: 1.1rem;
        color: var(--shenas-text, #2c2c28);
      }
      .hint {
        font-size: 0.9rem;
        color: var(--shenas-text-secondary, #5a5850);
        text-align: center;
        line-height: 1.45;
        margin: 0;
      }
      .open-btn {
        width: 100%;
        padding: 0.6rem 1rem;
        background: var(--shenas-primary, #728f67);
        color: #fff;
        border: none;
        border-radius: 5px;
        font-size: 0.92rem;
        cursor: pointer;
        font-weight: 500;
      }
      .open-btn:hover {
        background: var(--shenas-primary-hover, #5f7a56);
      }
      .cancel-link {
        display: block;
        text-align: center;
        font-size: 0.82rem;
        color: var(--shenas-text-muted, #8a8780);
        cursor: pointer;
        text-decoration: underline;
        background: none;
        border: none;
        padding: 0;
      }
      .cancel-link:hover {
        color: var(--shenas-text, #2c2c28);
      }
      .loading-text {
        text-align: center;
        color: var(--shenas-text-muted, #8a8780);
        font-size: 0.85rem;
        font-style: italic;
      }
      .polling-indicator {
        font-size: 0.78rem;
        color: var(--shenas-text-faint, #b0ada6);
        text-align: center;
        margin: 0;
      }
    `,
  ];

  declare apiBase: string;
  declare _phase: Phase;
  declare _errorMessage: string | null;

  private _state = "";
  private _authorizationUrl = "";
  private _pollTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    super();
    this.apiBase = "/api";
    this._phase = "loading";
    this._errorMessage = null;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._startFlow().catch(() => {
      /* handled inside _startFlow */
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._stopPolling();
  }

  private async _startFlow(): Promise<void> {
    this._phase = "loading";
    try {
      const resp = await fetch(`${this.apiBase}/auth/login`);
      const data = (await resp.json()) as LoginPayload;
      if (!resp.ok || data.error || !data.authorization_url) {
        this._errorMessage = data.error || "Failed to start sign-in flow.";
        this._phase = "error";
        return;
      }
      this._state = data.state;
      this._authorizationUrl = data.authorization_url;
      this._phase = "waiting";
      openExternal(this._authorizationUrl);
      this._pollTimer = setInterval(() => {
        void this._poll();
      }, 2000);
    } catch {
      this._errorMessage = "Network error — could not start sign-in.";
      this._phase = "error";
    }
  }

  private async _poll(): Promise<void> {
    try {
      const resp = await fetch(`${this.apiBase}/auth/status?state=${encodeURIComponent(this._state)}`);
      if (resp.status === 404) {
        this._stopPolling();
        this._errorMessage = "Sign-in session expired — try again.";
        this._phase = "error";
        return;
      }
      const data = (await resp.json()) as StatusPayload;
      if (data.status === "authorized") {
        this._stopPolling();
        this.dispatchEvent(new CustomEvent("auth-changed", { bubbles: true, composed: true }));
      } else if (data.status === "error") {
        this._stopPolling();
        this._errorMessage = data.error || "Sign-in failed.";
        this._phase = "error";
      }
      // status === "pending" → keep polling
    } catch {
      // Transient network error during poll — try again on next tick.
    }
  }

  private _stopPolling(): void {
    if (this._pollTimer !== null) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
  }

  private _cancel(): void {
    this._stopPolling();
    this.dispatchEvent(new CustomEvent("device-login-cancel", { bubbles: true, composed: true }));
  }

  render() {
    if (this._phase === "loading") {
      return html`
        <div class="dialog" @click=${(e: MouseEvent) => e.stopPropagation()}>
          <h2>Sign in with shenas.net</h2>
          <p class="loading-text">Starting sign-in&hellip;</p>
          <button class="cancel-link" @click=${() => this._cancel()}>Cancel</button>
        </div>
      `;
    }

    if (this._phase === "error") {
      return html`
        <div class="dialog" @click=${(e: MouseEvent) => e.stopPropagation()}>
          <h2>Sign in with shenas.net</h2>
          <div class="message error">${this._errorMessage}</div>
          <button class="cancel-link" @click=${() => this._cancel()}>Close</button>
        </div>
      `;
    }

    return html`
      <div class="dialog" @click=${(e: MouseEvent) => e.stopPropagation()}>
        <h2>Sign in with shenas.net</h2>
        <p class="hint">
          Your browser should have opened to the shenas.net sign-in page. Complete sign-in there to return here.
        </p>
        <button class="open-btn" @click=${() => openExternal(this._authorizationUrl)}>Reopen sign-in page</button>
        <p class="polling-indicator">Waiting for authorization&hellip;</p>
        <button class="cancel-link" @click=${() => this._cancel()}>Cancel</button>
      </div>
    `;
  }
}

customElements.define("shenas-device-login-modal", ShenasDeviceLoginModal);
