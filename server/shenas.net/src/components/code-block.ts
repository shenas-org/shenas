import { LitElement, html, css } from "lit";

export class CodeBlock extends LitElement {
  static override properties = {
    title: { type: String },
    _copied: { type: Boolean, state: true },
  };

  static override styles = css`
    :host {
      display: block;
    }

    .wrapper {
      background: var(--color-bg-elevated, #12121a);
      border: 1px solid var(--color-border, #2a2a3a);
      border-radius: 12px;
      overflow: hidden;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--color-border, #2a2a3a);
      background: var(--color-bg-card, #1a1a25);
    }

    .title {
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--color-text-muted, #8888a0);
      font-family: var(--font-mono, monospace);
    }

    .copy-btn {
      background: none;
      border: 1px solid var(--color-border, #2a2a3a);
      color: var(--color-text-muted, #8888a0);
      font-size: 0.75rem;
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      font-family: var(--font-mono, monospace);
      transition: all 0.15s;
    }

    .copy-btn:hover {
      border-color: var(--color-accent, #6c5ce7);
      color: var(--color-text, #e8e8ef);
    }

    pre {
      margin: 0;
      padding: 1.25rem;
      overflow-x: auto;
      scrollbar-width: thin;
    }

    code {
      font-family: var(--font-mono, monospace);
      font-size: 0.85rem;
      line-height: 1.7;
      color: var(--color-text, #e8e8ef);
    }
  `;

  title = "terminal";
  _copied = false;

  private async _copy() {
    const slot = this.shadowRoot?.querySelector("slot");
    const text = slot
      ?.assignedNodes()
      .map((n) => n.textContent)
      .join("")
      .trim();
    if (text) {
      await navigator.clipboard.writeText(text);
      this._copied = true;
      setTimeout(() => (this._copied = false), 2000);
    }
  }

  override render() {
    return html`
      <div class="wrapper">
        <div class="header">
          <span class="title">${this.title}</span>
          <button class="copy-btn" @click=${this._copy}>
            ${this._copied ? "copied" : "copy"}
          </button>
        </div>
        <pre><code><slot></slot></code></pre>
      </div>
    `;
  }
}

customElements.define("shenas-code-block", CodeBlock);
