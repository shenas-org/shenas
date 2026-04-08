import { LitElement, html, css } from "lit";
import { buttonStyles, formStyles, messageStyles } from "shenas-frontends";

interface LocalUser {
  id: number;
  username: string;
}

/**
 * Modal user-selection dialog shown when multi-user mode is enabled.
 *
 * Dispatches:
 *   @user-selected  { userId, username, token }  — on successful login/register
 *   @dialog-close                                 — on cancel (only when cancellable prop is set)
 */
class UserSelectDialog extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    cancellable: { type: Boolean },
    _users: { state: true },
    _expandedUserId: { state: true },
    _password: { state: true },
    _regUsername: { state: true },
    _regPassword: { state: true },
    _error: { state: true },
    _loading: { state: true },
  };

  static styles = [
    buttonStyles,
    formStyles,
    messageStyles,
    css`
      :host {
        display: block;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .dialog {
        background: var(--shenas-bg, #fff);
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 10px;
        padding: 2rem;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
      }
      h2 {
        margin: 0;
        font-size: 1.1rem;
        color: var(--shenas-text, #222);
      }
      .section-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--shenas-text-faint, #aaa);
        margin-bottom: 0.4rem;
      }
      .user-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .user-row {
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 6px;
        overflow: hidden;
      }
      .user-row-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.55rem 0.75rem;
        background: var(--shenas-bg-secondary, #f8f8f8);
      }
      .user-name {
        font-size: 0.95rem;
        color: var(--shenas-text, #222);
      }
      .user-row-body {
        padding: 0.65rem 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
      }
      .user-row-body input {
        width: 100%;
        box-sizing: border-box;
      }
      .divider {
        border: none;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
        margin: 0;
      }
      .register-form {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .register-form input {
        width: 100%;
        box-sizing: border-box;
      }
      .error {
        color: var(--shenas-error, #c62828);
        font-size: 0.85rem;
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
      }
      .shenas-net-btn {
        width: 100%;
        text-align: center;
        background: var(--shenas-bg-secondary, #f3f0eb);
        border: 1px solid var(--shenas-border, #d8d4cc);
      }
    `,
  ];

  declare apiBase: string;
  declare cancellable: boolean;
  declare _users: LocalUser[];
  declare _expandedUserId: number | null;
  declare _password: string;
  declare _regUsername: string;
  declare _regPassword: string;
  declare _error: string | null;
  declare _loading: boolean;

  constructor() {
    super();
    this.apiBase = "/api";
    this.cancellable = false;
    this._users = [];
    this._expandedUserId = null;
    this._password = "";
    this._regUsername = "";
    this._regPassword = "";
    this._error = null;
    this._loading = false;
  }

  async connectedCallback(): Promise<void> {
    super.connectedCallback();
    await this._loadUsers();
  }

  async _loadUsers(): Promise<void> {
    try {
      const resp = await fetch(`${this.apiBase}/users`);
      if (resp.ok) {
        this._users = (await resp.json()) as LocalUser[];
      }
    } catch {
      /* ignore */
    }
  }

  _expandUser(userId: number): void {
    if (this._expandedUserId === userId) {
      this._expandedUserId = null;
    } else {
      this._expandedUserId = userId;
      this._password = "";
      this._error = null;
    }
  }

  async _login(user: LocalUser): Promise<void> {
    if (!this._password) {
      this._error = "Enter your password";
      return;
    }
    this._loading = true;
    this._error = null;
    try {
      const resp = await fetch(`${this.apiBase}/users/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user.username, password: this._password }),
      });
      if (!resp.ok) {
        const err = (await resp.json()) as { detail?: string };
        this._error = err.detail || "Login failed";
        return;
      }
      const data = (await resp.json()) as { id: number; username: string; token: string };
      this._dispatch(data.id, data.username, data.token);
    } catch {
      this._error = "Login failed";
    } finally {
      this._loading = false;
    }
  }

  async _register(): Promise<void> {
    if (!this._regUsername.trim()) {
      this._error = "Enter a username";
      return;
    }
    if (!this._regPassword) {
      this._error = "Enter a password";
      return;
    }
    this._loading = true;
    this._error = null;
    try {
      const resp = await fetch(`${this.apiBase}/users/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: this._regUsername.trim(), password: this._regPassword }),
      });
      if (!resp.ok) {
        const err = (await resp.json()) as { detail?: string };
        this._error = err.detail || "Registration failed";
        return;
      }
      const data = (await resp.json()) as { id: number; username: string; token: string };
      this._dispatch(data.id, data.username, data.token);
    } catch {
      this._error = "Registration failed";
    } finally {
      this._loading = false;
    }
  }

  _dispatch(userId: number, username: string, token: string): void {
    this.dispatchEvent(
      new CustomEvent("user-selected", {
        bubbles: true,
        composed: true,
        detail: { userId, username, token },
      }),
    );
  }

  render() {
    return html`
      <div class="dialog" @click=${(e: MouseEvent) => e.stopPropagation()}>
        <h2>Select User</h2>

        ${this._error ? html`<p class="error">${this._error}</p>` : ""}
        ${this._users.length > 0
          ? html`
              <div>
                <p class="section-label">Existing users</p>
                <div class="user-list">
                  ${this._users.map(
                    (u) => html`
                      <div class="user-row">
                        <div class="user-row-header">
                          <span class="user-name">${u.username}</span>
                          <button @click=${() => this._expandUser(u.id)} ?disabled=${this._loading}>
                            ${this._expandedUserId === u.id ? "Cancel" : "Select"}
                          </button>
                        </div>
                        ${this._expandedUserId === u.id
                          ? html`
                              <div class="user-row-body">
                                <input
                                  type="password"
                                  placeholder="Password"
                                  .value=${this._password}
                                  @input=${(e: Event) => {
                                    this._password = (e.target as HTMLInputElement).value;
                                  }}
                                  @keydown=${(e: KeyboardEvent) => {
                                    if (e.key === "Enter") this._login(u);
                                  }}
                                  autofocus
                                />
                                <div class="actions">
                                  <button ?disabled=${this._loading} @click=${() => this._login(u)}>
                                    ${this._loading ? "..." : "Sign in"}
                                  </button>
                                </div>
                              </div>
                            `
                          : ""}
                      </div>
                    `,
                  )}
                </div>
              </div>
              <hr class="divider" />
            `
          : ""}

        <div>
          <p class="section-label">Register new user</p>
          <div class="register-form">
            <input
              type="text"
              placeholder="Username"
              .value=${this._regUsername}
              @input=${(e: Event) => {
                this._regUsername = (e.target as HTMLInputElement).value;
              }}
            />
            <input
              type="password"
              placeholder="Password"
              .value=${this._regPassword}
              @input=${(e: Event) => {
                this._regPassword = (e.target as HTMLInputElement).value;
              }}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === "Enter") this._register();
              }}
            />
            <button ?disabled=${this._loading} @click=${this._register}>
              ${this._loading ? "..." : "Create & Select"}
            </button>
          </div>
        </div>

        <hr class="divider" />

        <button
          class="shenas-net-btn"
          @click=${() => {
            window.location.href = "/api/auth/login";
          }}
        >
          Sign in with shenas.net
        </button>

        ${this.cancellable
          ? html`
              <div class="actions">
                <button
                  @click=${() => {
                    this.dispatchEvent(new CustomEvent("dialog-close", { bubbles: true, composed: true }));
                  }}
                >
                  Cancel
                </button>
              </div>
            `
          : ""}
      </div>
    `;
  }
}

customElements.define("shenas-user-select-dialog", UserSelectDialog);
