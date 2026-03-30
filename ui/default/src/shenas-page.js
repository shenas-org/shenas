import { LitElement, html } from "lit";
import { utilityStyles } from "./shared-styles.js";

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
  };

  static styles = [utilityStyles];

  constructor() {
    super();
    this.loading = false;
    this.empty = false;
    this.loadingText = "Loading...";
    this.emptyText = "No data";
  }

  render() {
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
