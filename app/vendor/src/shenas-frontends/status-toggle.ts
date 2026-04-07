import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";

class StatusToggle extends LitElement {
  static properties = {
    enabled: { type: Boolean, reflect: true },
    toggleable: { type: Boolean, reflect: true },
  };

  declare enabled: boolean;
  declare toggleable: boolean;

  static styles: CSSResult = css`
    :host {
      display: inline-block;
      vertical-align: middle;
    }
    .track {
      width: 28px;
      height: 16px;
      border-radius: 8px;
      background: var(--shenas-error, #c62828);
      position: relative;
      transition: background 0.2s;
    }
    :host([enabled]) .track {
      background: var(--shenas-success, #2e7d32);
    }
    .knob {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--shenas-bg, #fff);
      position: absolute;
      top: 2px;
      left: 2px;
      transition: left 0.2s;
    }
    :host([enabled]) .knob {
      left: 14px;
    }
    :host([toggleable]) .track {
      cursor: pointer;
    }
    :host([toggleable]:hover) .track {
      opacity: 0.85;
    }
  `;

  constructor() {
    super();
    this.enabled = false;
    this.toggleable = false;
  }

  updated(): void {
    this.title = this.enabled ? "Enabled" : "Disabled";
  }

  render(): TemplateResult {
    return html`<div class="track" @click=${this._onClick}><div class="knob"></div></div>`;
  }

  _onClick(): void {
    if (!this.toggleable) return;
    this.dispatchEvent(new CustomEvent("toggle", { bubbles: true, composed: true }));
  }
}

customElements.define("status-toggle", StatusToggle);
