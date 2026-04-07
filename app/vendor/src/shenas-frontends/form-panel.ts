import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResultGroup } from "lit";
import { buttonStyles } from "./shared-styles.ts";

/**
 * Shared form panel with title, slotted content, and action buttons.
 *
 * Usage:
 *   <shenas-form-panel
 *     title="New transform"
 *     submitLabel="Create"
 *     @submit=${this._save}
 *     @cancel=${this._cancel}
 *   >
 *     <div class="form-grid">...</div>
 *     <textarea ...></textarea>
 *   </shenas-form-panel>
 */
class FormPanel extends LitElement {
  static properties = {
    title: { type: String },
    submitLabel: { type: String, attribute: "submit-label" },
  };

  declare title: string;
  declare submitLabel: string;

  static styles: CSSResultGroup = [
    buttonStyles,
    css`
      :host {
        display: block;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
      }
      h3 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 0.8rem;
      }
    `,
  ];

  constructor() {
    super();
    this.title = "";
    this.submitLabel = "Save";
  }

  render(): TemplateResult {
    return html`
      ${this.title ? html`<h3>${this.title}</h3>` : ""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `;
  }

  _onSubmit(): void {
    this.dispatchEvent(new CustomEvent("submit", { bubbles: true, composed: true }));
  }

  _onCancel(): void {
    this.dispatchEvent(new CustomEvent("cancel", { bubbles: true, composed: true }));
  }
}

customElements.define("shenas-form-panel", FormPanel);
