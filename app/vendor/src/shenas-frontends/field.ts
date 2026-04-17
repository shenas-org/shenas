import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResultGroup } from "lit";

/**
 * Form field wrapper with label + input/textarea.
 *
 * Usage:
 *   <shenas-field label="Name" value=${name} @change=${e => ...}></shenas-field>
 *   <shenas-field label="Description" type="textarea" value=${desc} @change=${e => ...}></shenas-field>
 *   <shenas-field label="API Key" type="password" @change=${e => ...}></shenas-field>
 */
class ShenasField extends LitElement {
  static properties = {
    label: { type: String },
    type: { type: String },
    value: { type: String },
    placeholder: { type: String },
    readonly: { type: Boolean },
  };

  declare label: string;
  declare type: string;
  declare value: string;
  declare placeholder: string;
  declare readonly: boolean;

  static styles: CSSResultGroup = css`
    :host {
      display: block;
      margin-bottom: 0.6rem;
    }
    label {
      display: block;
      font-size: 0.8rem;
      color: var(--shenas-text-secondary, #666);
      margin-bottom: 0.2rem;
    }
    input,
    textarea {
      width: 100%;
      padding: 0.4rem 0.6rem;
      border: 1px solid var(--shenas-border-input, #ddd);
      border-radius: 4px;
      font-size: 0.85rem;
      box-sizing: border-box;
      background: var(--shenas-bg, #fff);
      color: var(--shenas-text, #222);
      font-family: inherit;
    }
    textarea {
      resize: vertical;
      min-height: 3rem;
    }
    input:read-only,
    textarea:read-only {
      opacity: 0.7;
      cursor: default;
    }
  `;

  constructor() {
    super();
    this.label = "";
    this.type = "text";
    this.value = "";
    this.placeholder = "";
    this.readonly = false;
  }

  render(): TemplateResult {
    return html`
      <label>${this.label}</label>
      ${this.type === "textarea"
        ? html`<textarea
            .value=${this.value}
            placeholder=${this.placeholder}
            ?readonly=${this.readonly}
            @input=${this._onInput}
          ></textarea>`
        : html`<input
            type=${this.type}
            .value=${this.value}
            placeholder=${this.placeholder}
            ?readonly=${this.readonly}
            @input=${this._onInput}
          />`}
    `;
  }

  _onInput(e: Event): void {
    const target = e.target as HTMLInputElement | HTMLTextAreaElement;
    this.value = target.value;
    this.dispatchEvent(new CustomEvent("change", { detail: { value: target.value }, bubbles: true, composed: true }));
  }
}

customElements.define("shenas-field", ShenasField);
