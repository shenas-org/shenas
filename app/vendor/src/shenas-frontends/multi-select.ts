import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResultGroup } from "lit";

/**
 * Multi-select checkbox list with label and search.
 *
 * Usage:
 *   <shenas-multi-select
 *     label="Places"
 *     .options=${[{value: "uuid1", label: "Amsterdam"}, ...]}
 *     .value=${["uuid1", "uuid3"]}
 *     @change=${e => console.log(e.detail.value)}
 *   ></shenas-multi-select>
 */

interface MultiSelectOption {
  value: string;
  label: string;
}

class ShenasMultiSelect extends LitElement {
  static properties = {
    label: { type: String },
    value: { type: Array },
    options: { type: Array },
    _filter: { state: true },
  };

  declare label: string;
  declare value: string[];
  declare options: MultiSelectOption[];
  declare _filter: string;

  static styles: CSSResultGroup = css`
    :host {
      display: block;
      margin-bottom: 0.6rem;
    }
    .label {
      display: block;
      font-size: 0.8rem;
      color: var(--shenas-text-secondary, #666);
      margin-bottom: 0.2rem;
    }
    .search {
      width: 100%;
      padding: 0.3rem 0.5rem;
      border: 1px solid var(--shenas-border-input, #ddd);
      border-radius: 4px;
      font-size: 0.8rem;
      box-sizing: border-box;
      margin-bottom: 0.3rem;
    }
    .list {
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid var(--shenas-border-input, #ddd);
      border-radius: 4px;
      background: var(--shenas-bg, #fff);
    }
    .option {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.3rem 0.5rem;
      font-size: 0.85rem;
      cursor: pointer;
      border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
    }
    .option:last-child {
      border-bottom: none;
    }
    .option:hover {
      background: var(--shenas-bg-hover, #f5f5f5);
    }
    .option input {
      margin: 0;
    }
    .count {
      font-size: 0.75rem;
      color: var(--shenas-text-muted, #888);
      margin-top: 0.2rem;
    }
  `;

  constructor() {
    super();
    this.label = "";
    this.value = [];
    this.options = [];
    this._filter = "";
  }

  render(): TemplateResult {
    const filter = this._filter.toLowerCase();
    const filtered = filter
      ? this.options.filter((option) => option.label.toLowerCase().includes(filter))
      : this.options;
    const selected = new Set(this.value);
    return html`
      <span class="label">${this.label}</span>
      ${this.options.length > 8
        ? html`<input
            class="search"
            type="text"
            placeholder="Filter..."
            .value=${this._filter}
            @input=${(e: InputEvent) => {
              this._filter = (e.target as HTMLInputElement).value;
            }}
          />`
        : ""}
      <div class="list">
        ${filtered.map(
          (option) => html`
            <label class="option">
              <input
                type="checkbox"
                .checked=${selected.has(option.value)}
                @change=${() => this._toggle(option.value)}
              />
              ${option.label}
            </label>
          `,
        )}
      </div>
      <div class="count">${selected.size} of ${this.options.length} selected</div>
    `;
  }

  _toggle(optionValue: string): void {
    const selected = new Set(this.value);
    if (selected.has(optionValue)) {
      selected.delete(optionValue);
    } else {
      selected.add(optionValue);
    }
    this.value = [...selected];
    this.dispatchEvent(new CustomEvent("change", { detail: { value: this.value }, bubbles: true, composed: true }));
  }
}

customElements.define("shenas-multi-select", ShenasMultiSelect);
