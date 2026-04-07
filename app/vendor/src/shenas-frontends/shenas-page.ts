import { LitElement, css, html } from "lit";
import type { TemplateResult, CSSResultGroup, PropertyValues } from "lit";
import { utilityStyles } from "./shared-styles.ts";

/**
 * Wrapper component that handles loading and empty state guards.
 *
 * Usage:
 *   <shenas-page ?loading=${this._loading} ?empty=${!this._data} empty-text="No items">
 *     ...content rendered only when not loading and not empty...
 *   </shenas-page>
 *
 * Props:
 *   loading      - show "Loading..." when true
 *   empty        - show empty-text when true (and not loading)
 *   loading-text - override the loading message (default: "Loading...")
 *   empty-text   - override the empty message (default: "No data")
 */
class ShenasPage extends LitElement {
  static properties = {
    loading: { type: Boolean, reflect: true },
    empty: { type: Boolean, reflect: true },
    loadingText: { type: String, attribute: "loading-text" },
    emptyText: { type: String, attribute: "empty-text" },
    displayName: { type: String, attribute: "display-name" },
  };

  declare loading: boolean;
  declare empty: boolean;
  declare loadingText: string;
  declare emptyText: string;
  declare displayName: string;

  static styles: CSSResultGroup = [
    utilityStyles,
    css`
      :host([loading]), :host([empty]) {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100%;
      }
      .loading, .empty {
        color: var(--shenas-text-muted, #888);
      }
    `,
  ];

  constructor() {
    super();
    this.loading = false;
    this.empty = false;
    this.loadingText = "Loading...";
    this.emptyText = "No data";
    this.displayName = "";
  }

  updated(changed: PropertyValues): void {
    if (changed.has("displayName") && this.displayName) {
      this.dispatchEvent(new CustomEvent("page-title", {
        bubbles: true,
        composed: true,
        detail: { title: this.displayName },
      }));
    }
  }

  render(): TemplateResult {
    if (this.loading) {
      return html`<p class="loading">${this.loadingText}</p>`;
    }
    if (this.empty) {
      return html`<p class="empty">${this.emptyText}</p>`;
    }
    return html`<slot></slot>`;
  }
}

customElements.define("shenas-page", ShenasPage);
