import { LitElement, html, css } from "lit";
import type { CSSResultGroup, TemplateResult } from "lit";

/**
 * Inline badge / pill label.
 *
 * Usage:
 *   <shenas-badge>event</shenas-badge>
 *   <shenas-badge variant="success">enabled</shenas-badge>
 *   <shenas-badge variant="error">ERROR</shenas-badge>
 *   <shenas-badge variant="warning">WARNING</shenas-badge>
 *   <shenas-badge variant="info">INFO</shenas-badge>
 */
class ShenasBadge extends LitElement {
  static properties = {
    variant: { type: String, reflect: true },
  };

  declare variant: string;

  constructor() {
    super();
    this.variant = "";
  }

  static styles: CSSResultGroup = css`
    :host {
      display: inline-block;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 3px;
      background: var(--shenas-border-light, #f0f0f0);
      color: var(--shenas-text-muted, #888);
      vertical-align: middle;
      line-height: 1.4;
    }
    :host([variant="success"]) {
      background: var(--shenas-accent-soft, #e8efe4);
      color: var(--shenas-primary, #728f67);
    }
    :host([variant="info"]) {
      background: var(--shenas-bg-selected, #f0f4ff);
      color: var(--shenas-primary, #0066cc);
    }
    :host([variant="warning"]) {
      background: #fff3e0;
      color: #f57c00;
    }
    :host([variant="error"]) {
      background: var(--shenas-danger-bg, #fce4ec);
      color: var(--shenas-error, #c62828);
    }
    :host([variant="debug"]) {
      background: var(--shenas-bg-secondary, #fafafa);
      color: var(--shenas-text-muted, #888);
    }
  `;

  render(): TemplateResult {
    return html`<slot></slot>`;
  }
}

customElements.define("shenas-badge", ShenasBadge);
