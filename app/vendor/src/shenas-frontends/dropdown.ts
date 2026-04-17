import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResultGroup } from "lit";

/**
 * Dropdown select field with label.
 *
 * Usage:
 *   <shenas-dropdown
 *     label="Type"
 *     .options=${[{value: "human", label: "Human"}, ...]}
 *     value=${selectedType}
 *     @change=${e => ...}
 *   ></shenas-dropdown>
 *
 *   <!-- With placeholder -->
 *   <shenas-dropdown
 *     label="Pick one..."
 *     placeholder="Select..."
 *     .options=${items}
 *     @change=${e => ...}
 *   ></shenas-dropdown>
 */

interface DropdownOption {
  value: string;
  label: string;
  disabled?: boolean;
}

class ShenasDropdown extends LitElement {
  static properties = {
    label: { type: String },
    value: { type: String },
    placeholder: { type: String },
    options: { type: Array },
    disabled: { type: Boolean },
  };

  declare label: string;
  declare value: string;
  declare placeholder: string;
  declare options: DropdownOption[];
  declare disabled: boolean;

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
    select {
      width: 100%;
      padding: 0.4rem 0.6rem;
      border: 1px solid var(--shenas-border-input, #ddd);
      border-radius: 4px;
      font-size: 0.85rem;
      box-sizing: border-box;
      background: var(--shenas-bg, #fff);
      color: var(--shenas-text, #222);
    }
  `;

  constructor() {
    super();
    this.label = "";
    this.value = "";
    this.placeholder = "";
    this.options = [];
    this.disabled = false;
  }

  render(): TemplateResult {
    return html`
      <label>${this.label}</label>
      <select .value=${this.value} ?disabled=${this.disabled} @change=${this._onChange}>
        ${this.placeholder ? html`<option value="" ?selected=${!this.value} disabled>${this.placeholder}</option>` : ""}
        ${this.options.map(
          (opt) => html`
            <option value=${opt.value} ?selected=${this.value === opt.value} ?disabled=${opt.disabled ?? false}>
              ${opt.label}
            </option>
          `,
        )}
      </select>
    `;
  }

  _onChange(e: Event): void {
    const target = e.target as HTMLSelectElement;
    this.value = target.value;
    this.dispatchEvent(new CustomEvent("change", { detail: { value: target.value }, bubbles: true, composed: true }));
  }
}

customElements.define("shenas-dropdown", ShenasDropdown);
