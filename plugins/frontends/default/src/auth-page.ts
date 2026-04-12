import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";

interface AuthRequest {
  code: string;
  challenge: string;
}

export class AuthPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _authRequest: { state: true },
    _error: { state: true },
    _loading: { state: true },
  };

  declare apiBase: string;
  declare _authRequest: AuthRequest | null;
  declare _error: string | null;
  declare _loading: boolean;

  get deviceCodeInput(): HTMLInputElement | null {
    return this.renderRoot?.querySelector("#device-code") as HTMLInputElement | null;
  }

  static styles: CSSResult = css`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      font-family: var(--shenas-font, system-ui, sans-serif);
    }

    .container {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 12px;
      padding: 2rem;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .logo {
      text-align: center;
      margin-bottom: 2rem;
    }

    .logo h1 {
      font-size: 1.8rem;
      margin: 0;
      color: var(--shenas-accent, #6c5ce7);
      font-weight: 700;
    }

    .logo p {
      color: var(--shenas-text-muted, #a8a8c0);
      margin: 0.5rem 0 0 0;
      font-size: 0.9rem;
    }

    .form-group {
      margin-bottom: 1.5rem;
    }

    label {
      display: block;
      margin-bottom: 0.5rem;
      color: var(--shenas-text, #e8e8ef);
      font-size: 0.9rem;
      font-weight: 500;
    }

    input {
      width: 100%;
      padding: 0.75rem;
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 6px;
      background: var(--shenas-surface-alt, #2a2a3a);
      color: var(--shenas-text, #e8e8ef);
      font-size: 0.95rem;
      box-sizing: border-box;
    }

    input:focus {
      outline: none;
      border-color: var(--shenas-accent, #6c5ce7);
      box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1);
    }

    button {
      width: 100%;
      padding: 0.75rem;
      background: var(--shenas-accent, #6c5ce7);
      border: none;
      border-radius: 6px;
      color: white;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition:
        opacity 0.2s,
        transform 0.2s;
    }

    button:hover {
      opacity: 0.9;
      transform: translateY(-2px);
    }

    button:active {
      transform: translateY(0);
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    .error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;
      padding: 0.75rem;
      border-radius: 6px;
      margin-bottom: 1rem;
      font-size: 0.9rem;
    }

    .success {
      background: rgba(34, 197, 94, 0.1);
      border: 1px solid rgba(34, 197, 94, 0.3);
      color: #22c55e;
      padding: 0.75rem;
      border-radius: 6px;
      margin-bottom: 1rem;
      font-size: 0.9rem;
    }

    .info {
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #3b82f6;
      padding: 0.75rem;
      border-radius: 6px;
      margin-bottom: 1rem;
      font-size: 0.9rem;
    }
  `;

  constructor() {
    super();
    this.apiBase = "";
    this._authRequest = null;
    this._error = null;
    this._loading = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this.initializeAuth();
  }

  private async initializeAuth() {
    this._loading = true;
    this._error = null;

    try {
      const response = await fetch(`${this.apiBase}/api/auth/request`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to initialize authentication");
      }

      const data = await response.json();
      this._authRequest = data;
    } catch (error) {
      this._error = error instanceof Error ? error.message : String(error);
    } finally {
      this._loading = false;
    }
  }

  private async handleSubmit(event: Event) {
    event.preventDefault();
    this._loading = true;
    this._error = null;

    try {
      const code = this.deviceCodeInput?.value;
      if (!code) {
        throw new Error("Device code is required");
      }

      const response = await fetch(`${this.apiBase}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          challenge: this._authRequest?.challenge,
        }),
      });

      if (!response.ok) {
        throw new Error("Invalid device code");
      }

      const data = await response.json();
      if (data.token) {
        localStorage.setItem("auth_token", data.token);
        window.location.href = "/";
      }
    } catch (error) {
      this._error = error instanceof Error ? error.message : String(error);
    } finally {
      this._loading = false;
    }
  }

  render(): TemplateResult {
    return html`
      <div class="container">
        <div class="logo">
          <h1>Shenas</h1>
          <p>Personal data integration</p>
        </div>

        ${this._error ? html`<div class="error">${this._error}</div>` : ""}
        ${this._authRequest
          ? html`
              <div class="info">Enter your device code below to authenticate</div>
              <form @submit=${this.handleSubmit.bind(this)}>
                <div class="form-group">
                  <label for="device-code">Device Code</label>
                  <input id="device-code" type="text" placeholder="Enter device code" required />
                </div>
                <button type="submit" ?disabled=${this._loading}>
                  ${this._loading ? "Authenticating..." : "Authenticate"}
                </button>
              </form>
            `
          : ""}
      </div>
    `;
  }
}

customElements.define("shenas-auth-page", AuthPage);
