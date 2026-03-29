import { LitElement, html, css } from "lit";

class StatusDot extends LitElement {
  static properties = {
    enabled: { type: Boolean, reflect: true },
    toggleable: { type: Boolean, reflect: true },
  };

  static styles = css`
    :host {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      vertical-align: middle;
      transition: background 0.15s;
    }
    :host([enabled]) {
      background: #2e7d32;
    }
    :host(:not([enabled])) {
      background: #c62828;
    }
    :host([toggleable]) {
      cursor: pointer;
    }
    :host([toggleable]:hover) {
      box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
    }
  `;

  constructor() {
    super();
    this.enabled = false;
    this.toggleable = false;
  }

  updated() {
    this.title = this.enabled ? "Enabled" : "Disabled";
  }

  render() {
    return html``;
  }

  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("click", this._onClick);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("click", this._onClick);
  }

  _onClick = () => {
    if (!this.toggleable) return;
    this.dispatchEvent(new CustomEvent("toggle", { bubbles: true, composed: true }));
  };
}

customElements.define("status-dot", StatusDot);
