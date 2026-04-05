import { LitElement, html, css } from "lit";

export class FeatureCard extends LitElement {
  static override properties = {
    icon: { type: String },
    heading: { type: String },
  };

  static override styles = css`
    :host {
      display: block;
    }

    .card {
      background: var(--color-bg-card, #1a1a25);
      border: 1px solid var(--color-border, #2a2a3a);
      border-radius: 16px;
      padding: 2rem;
      height: 100%;
      transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
    }

    .card:hover {
      border-color: var(--color-accent, #728f67);
      transform: translateY(-2px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
    }

    .icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      font-weight: 600;
      font-family: var(--font-mono, monospace);
      margin-bottom: 1.25rem;
      background: var(--color-accent-glow, rgba(108, 92, 231, 0.15));
      color: var(--color-accent-light, #a3bd97);
      border: 1px solid color-mix(in srgb, var(--color-accent-light, #a3bd97) 20%, transparent);
    }

    h3 {
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 0.75rem;
      color: var(--color-text, #e8e8ef);
    }

    p {
      font-size: 0.9rem;
      line-height: 1.6;
      color: var(--color-text-muted, #8888a0);
    }
  `;

  icon = "";
  heading = "";

  override render() {
    return html`
      <div class="card">
        <div class="icon">${this.icon}</div>
        <h3>${this.heading}</h3>
        <p><slot></slot></p>
      </div>
    `;
  }
}

customElements.define("shenas-feature-card", FeatureCard);
