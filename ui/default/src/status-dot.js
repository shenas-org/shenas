import { LitElement, html, css } from "lit";

class StatusDot extends LitElement {
  static properties = {
    enabled: { type: Boolean, reflect: true },
  };

  static styles = css`
    :host {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      vertical-align: middle;
    }
    :host([enabled]) {
      background: #2e7d32;
    }
    :host(:not([enabled])) {
      background: #c62828;
    }
  `;

  constructor() {
    super();
    this.enabled = false;
  }

  updated() {
    this.title = this.enabled ? "Enabled" : "Disabled";
  }

  render() {
    return html``;
  }
}

customElements.define("status-dot", StatusDot);
