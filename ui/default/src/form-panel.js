import { LitElement, html, css } from "lit";
import { buttonStyles } from "./shared-styles.js";

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

  static styles = [
    buttonStyles,
    css`
      :host {
        display: block;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: #fafafa;
      }
      h3 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
      }
      .actions {
        display: flex;
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

  render() {
    return html`
      ${this.title ? html`<h3>${this.title}</h3>` : ""}
      <slot></slot>
      <div class="actions">
        <button @click=${this._onSubmit}>${this.submitLabel}</button>
        <button @click=${this._onCancel}>Cancel</button>
      </div>
    `;
  }

  _onSubmit() {
    this.dispatchEvent(new CustomEvent("submit", { bubbles: true, composed: true }));
  }

  _onCancel() {
    this.dispatchEvent(new CustomEvent("cancel", { bubbles: true, composed: true }));
  }
}

customElements.define("shenas-form-panel", FormPanel);
