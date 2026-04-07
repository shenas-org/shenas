import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult, PropertyValues } from "lit";
import type { CommandDescriptor } from "./api.ts";

class CommandPalette extends LitElement {
  static properties = {
    open: { type: Boolean, reflect: true },
    commands: { type: Array },
    _query: { state: true },
    _filtered: { state: true },
    _selectedIndex: { state: true },
  };

  declare open: boolean;
  declare commands: CommandDescriptor[];
  declare _query: string;
  declare _filtered: CommandDescriptor[];
  declare _selectedIndex: number;

  static styles: CSSResult = css`
    :host {
      display: none;
    }
    :host([open]) {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 10000;
    }
    .backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
    }
    .panel {
      position: relative;
      width: 90%;
      max-width: 560px;
      margin: 80px auto 0;
      background: var(--shenas-bg, #fff);
      border-radius: 8px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
      display: flex;
      flex-direction: column;
      max-height: 60vh;
      overflow: hidden;
    }
    .input-row {
      display: flex;
      align-items: center;
      padding: 0 1rem;
      border-bottom: 1px solid var(--shenas-border, #e0e0e0);
    }
    .search-icon {
      color: var(--shenas-text-faint, #aaa);
      font-size: 0.9rem;
      margin-right: 0.5rem;
    }
    input {
      flex: 1;
      padding: 0.8rem 0;
      border: none;
      font-size: 0.95rem;
      outline: none;
      background: transparent;
      color: var(--shenas-text, #222);
    }
    .hint {
      font-size: 0.7rem;
      color: var(--shenas-text-faint, #aaa);
      font-family: monospace;
    }
    .results {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
    .item {
      padding: 0.5rem 1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
    }
    .item:hover,
    .item.selected {
      background: var(--shenas-bg-selected, #f0f4ff);
    }
    .item-category {
      color: var(--shenas-text-muted, #888);
      font-size: 0.75rem;
      min-width: 60px;
    }
    .item-label {
      flex: 1;
      color: var(--shenas-text, #222);
    }
    .item-desc {
      color: var(--shenas-text-faint, #aaa);
      font-size: 0.75rem;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .empty {
      padding: 1.5rem;
      text-align: center;
      color: var(--shenas-text-muted, #888);
      font-size: 0.85rem;
    }
  `;

  constructor() {
    super();
    this.open = false;
    this.commands = [];
    this._query = "";
    this._filtered = [];
    this._selectedIndex = 0;
  }

  willUpdate(changed: PropertyValues): void {
    if (changed.has("open") && this.open) {
      this._query = "";
      this._selectedIndex = 0;
      this._filter();
    }
    if (changed.has("commands")) {
      this._filter();
    }
  }

  updated(changed: PropertyValues): void {
    if (changed.has("open") && this.open) {
      requestAnimationFrame(() => {
        const input = (this.renderRoot as ShadowRoot).querySelector("input");
        if (input) input.focus();
      });
    }
  }

  _filter(): void {
    const q = this._query.toLowerCase();
    if (!q) {
      this._filtered = this.commands;
    } else {
      this._filtered = this.commands.filter(
        (c) =>
          c.label.toLowerCase().includes(q) ||
          c.category.toLowerCase().includes(q) ||
          (c.description || "").toLowerCase().includes(q),
      );
    }
    if (this._selectedIndex >= this._filtered.length) {
      this._selectedIndex = Math.max(0, this._filtered.length - 1);
    }
  }

  _onInput(e: Event): void {
    this._query = (e.target as HTMLInputElement).value;
    this._selectedIndex = 0;
    this._filter();
  }

  _onKeydown(e: KeyboardEvent): void {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (this._filtered.length > 0) {
        this._selectedIndex = Math.min(this._selectedIndex + 1, this._filtered.length - 1);
      }
      this._scrollToSelected();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this._selectedIndex = Math.max(this._selectedIndex - 1, 0);
      this._scrollToSelected();
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = this._filtered[this._selectedIndex];
      if (cmd) this._execute(cmd);
    } else if (e.key === "Escape") {
      this._close();
    }
  }

  _scrollToSelected(): void {
    requestAnimationFrame(() => {
      const item = (this.renderRoot as ShadowRoot).querySelector(".item.selected");
      if (item) item.scrollIntoView({ block: "nearest" });
    });
  }

  _execute(cmd: CommandDescriptor): void {
    this.dispatchEvent(new CustomEvent("execute", { detail: cmd, bubbles: true, composed: true }));
  }

  _close(): void {
    this.dispatchEvent(new CustomEvent("close", { bubbles: true, composed: true }));
  }

  render(): TemplateResult {
    if (!this.open) return html``;
    return html`
      <div class="backdrop" @click=${this._close}></div>
      <div class="panel">
        <div class="input-row">
          <span class="search-icon">></span>
          <input
            type="text"
            placeholder="Type a command..."
            .value=${this._query}
            @input=${this._onInput}
            @keydown=${this._onKeydown}
          />
          <span class="hint">esc</span>
        </div>
        <div class="results">
          ${this._filtered.length === 0
            ? html`<div class="empty">No matching commands</div>`
            : this._filtered.map(
                (cmd, i) => html`
                  <div
                    class="item ${i === this._selectedIndex ? "selected" : ""}"
                    @click=${() => this._execute(cmd)}
                    @mouseenter=${() => {
                      this._selectedIndex = i;
                    }}
                  >
                    <span class="item-category">${cmd.category}</span>
                    <span class="item-label">${cmd.label}</span>
                    ${cmd.description ? html`<span class="item-desc">${cmd.description}</span>` : ""}
                  </div>
                `,
              )}
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-command-palette", CommandPalette);
