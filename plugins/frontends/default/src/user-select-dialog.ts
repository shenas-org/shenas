import { LitElement, html, css } from "lit";
import { buttonStyles, formStyles, messageStyles } from "shenas-frontends";

interface LocalUser {
  id: number;
  username: string;
}

/**
 * Modal dialog for local user selection and registration.
 *
 * Dispatches:
 * - `user-selected` with `{ userId, username, token }` on successful login
 * - `dialog-close` on cancel (only when `cancelable` is true)
 */
class UserSelectDialog extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    cancelable: { type: Boolean },
    _users: { state: true },
    _selectedUser: { state: true },
    _showPasswordPrompt: { state: true },
    _password: { state: true },
    _regUsername: { state: true },
    _regPassword: { state: true },
    _error: { state: true },
    _loading: { state: true },
  };

  declare apiBase: string;
  declare cancelable: boolean;
  declare _users: LocalUser[];
  declare _selectedUser: LocalUser | null;
  declare _showPasswordPrompt: boolean;
  declare _password: string;
  declare _regUsername: string;
  declare _regPassword: string;
  declare _error: string;
  declare _loading: boolean;

  constructor() {
    super();
    this.apiBase = "/api";
    this.cancelable = false;
    this._users = [];
    this._selectedUser = null;
    this._showPasswordPrompt = false;
    this._password = "";
    this._regUsername = "";
    this._regPassword = "";
    this._error = "";
    this._loading = false;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._loadUsers();
  }

  async _loadUsers(): Promise<void> {
    try {
      const res = await fetch(`${this.apiBase}/users`);
      this._users = res.ok ? await res.json() : [];
    } catch {
      this._users = [];
    }
  }

  _selectUser(user: LocalUser): void {
    this._selectedUser = user;
    this._showPasswordPrompt = true;
    this._password = "";
    this._error = "";
  }

  async _login(): Promise<void> {
    if (!this._selectedUser) return;
    this._loading = true;
    this._error = "";
    try {
      const res = await fetch(`${this.apiBase}/users/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: this._selectedUser.username, password: this._password }),
      });
      const data = await res.json();
      if (!res.ok) {
        this._error = data.detail || "Invalid password";
        return;
      }
      this.dispatchEvent(
        new CustomEvent("user-selected", {
          detail: { userId: data.user.id, username: data.user.username, token: data.token },
          bubbles: true,
          composed: true,
        }),
      );
    } catch {
      this._error = "Login failed";
    } finally {
      this._loading = false;
    }
  }

  async _register(): Promise<void> {
    if (!this._regUsername || !this._regPassword) {
      this._error = "Username and password are required";
      return;
    }
    this._loading = true;
    this._error = "";
    try {
      const res = await fetch(`${this.apiBase}/users/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: this._regUsername, password: this._regPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        this._error = data.detail || "Registration failed";
        return;
      }
      this.dispatchEvent(
        new CustomEvent("user-selected", {
          detail: { userId: data.user.id, username: data.user.username, token: data.token },
          bubbles: true,
          composed: true,
        }),
      );
    } catch {
      this._error = "Registration failed";
    } finally {
      this._loading = false;
    }
  }

  _cancel(): void {
    this.dispatchEvent(new CustomEvent("dialog-close", { bubbles: true, composed: true }));
  }

  static styles = [
    buttonStyles,
    formStyles,
    messageStyles,
    css`
      :host {
        position: fixed;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.5);
        z-index: 1000;
      }
      .dialog {
        background: var(--shenas-bg, #fff);
        border-radius: 12px;
        padding: 2rem;
        width: min(420px, 90vw);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
      }
      h2 {
        margin: 0 0 1.5rem;
        font-size: 1.2rem;
        font-weight: 600;
      }
      .user-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
      }
      .user-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.6rem 0.8rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 6px;
        background: var(--shenas-bg-secondary, #fafafa);
      }
      .user-row.selected {
        border-color: var(--shenas-accent, #0066cc);
        background: var(--shenas-bg-selected, #f0f4ff);
      }
      .username {
        font-weight: 500;
      }
      .divider {
        border: none;
        border-top: 1px solid var(--shenas-border, #e0e0e0);
        margin: 1rem 0;
      }
      .section-label {
        font-size: 0.82rem;
        color: var(--shenas-text-secondary, #666);
        margin-bottom: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .password-prompt {
        margin-bottom: 1rem;
      }
      .error {
        color: var(--shenas-error, #c00);
        font-size: 0.85rem;
        margin-top: 0.5rem;
      }
      .actions {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        margin-top: 1rem;
      }
      .shenas-link {
        display: block;
        text-align: center;
        color: var(--shenas-accent, #0066cc);
        font-size: 0.9rem;
        text-decoration: none;
        margin-top: 0.5rem;
        cursor: pointer;
      }
      .shenas-link:hover {
        text-decoration: underline;
      }
    `,
  ];

  render() {
    return html`
      <div class="dialog">
        <h2>Select User</h2>

        ${this._users.length > 0
          ? html`
              <div class="section-label">Existing users</div>
              <div class="user-list">
                ${this._users.map(
                  (u) => html`
                    <div class="user-row ${this._selectedUser?.id === u.id ? "selected" : ""}">
                      <span class="username">${u.username}</span>
                      <button class="btn btn-sm" @click=${() => this._selectUser(u)}>Select</button>
                    </div>
                    ${this._selectedUser?.id === u.id && this._showPasswordPrompt
                      ? html`
                          <div class="password-prompt">
                            <input
                              class="input"
                              type="password"
                              placeholder="Password"
                              .value=${this._password}
                              @input=${(e: InputEvent) => (this._password = (e.target as HTMLInputElement).value)}
                              @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this._login()}
                            />
                            <div class="actions">
                              <button
                                class="btn btn-sm"
                                @click=${() => {
                                  this._showPasswordPrompt = false;
                                  this._selectedUser = null;
                                }}
                              >
                                Cancel
                              </button>
                              <button class="btn btn-sm btn-primary" ?disabled=${this._loading} @click=${this._login}>
                                ${this._loading ? "..." : "Sign in"}
                              </button>
                            </div>
                          </div>
                        `
                      : ""}
                  `,
                )}
              </div>
              <hr class="divider" />
            `
          : ""}

        <div class="section-label">Register new user</div>
        <input
          class="input"
          type="text"
          placeholder="Username"
          .value=${this._regUsername}
          @input=${(e: InputEvent) => (this._regUsername = (e.target as HTMLInputElement).value)}
        />
        <input
          class="input"
          type="password"
          placeholder="Password"
          .value=${this._regPassword}
          @input=${(e: InputEvent) => (this._regPassword = (e.target as HTMLInputElement).value)}
          @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this._register()}
          style="margin-top:0.5rem"
        />
        ${this._error ? html`<div class="error">${this._error}</div>` : ""}
        <div class="actions">
          ${this.cancelable ? html`<button class="btn btn-sm" @click=${this._cancel}>Cancel</button>` : ""}
          <button class="btn btn-sm btn-primary" ?disabled=${this._loading} @click=${this._register}>
            ${this._loading ? "..." : "Create & Select"}
          </button>
        </div>

        <hr class="divider" />
        <a class="shenas-link" href="/api/auth/login">Sign in with shenas.net</a>
      </div>
    `;
  }
}

customElements.define("user-select-dialog", UserSelectDialog);
