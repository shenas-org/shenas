import { LitElement, html, css } from "lit";

export class DataFlow extends LitElement {
  static override styles = css`
    :host {
      display: block;
      width: 100%;
      overflow: hidden;
    }

    .pipeline {
      display: flex;
      align-items: center;
      gap: 0;
      padding: 2rem 0;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .pipeline::-webkit-scrollbar {
      display: none;
    }

    .stage {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
      min-width: 140px;
      flex-shrink: 0;
      opacity: 0;
      transform: translateY(12px);
      animation: fadeUp 0.5s ease forwards;
    }

    .stage:nth-child(1) { animation-delay: 0s; }
    .stage:nth-child(3) { animation-delay: 0.15s; }
    .stage:nth-child(5) { animation-delay: 0.3s; }
    .stage:nth-child(7) { animation-delay: 0.45s; }
    .stage:nth-child(9) { animation-delay: 0.6s; }

    @keyframes fadeUp {
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .icon-box {
      width: 64px;
      height: 64px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.75rem;
      font-family: var(--font-mono, monospace);
      background: var(--color-bg-card, #1a1a25);
      border: 1px solid var(--color-border, #2a2a3a);
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .stage:hover .icon-box {
      border-color: var(--color-accent, #6c5ce7);
      box-shadow: 0 0 20px var(--color-accent-glow, rgba(108, 92, 231, 0.15));
    }

    .label {
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--color-text, #e8e8ef);
      text-align: center;
    }

    .sublabel {
      font-size: 0.7rem;
      color: var(--color-text-muted, #8888a0);
      text-align: center;
    }

    .arrow {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      padding: 0 0.25rem;
      color: var(--color-text-muted, #8888a0);
    }

    .arrow svg {
      width: 32px;
      height: 16px;
    }

    .arrow .pulse-dot {
      animation: pulse 2s ease-in-out infinite;
    }

    .arrow:nth-child(2) .pulse-dot { animation-delay: 0s; }
    .arrow:nth-child(4) .pulse-dot { animation-delay: 0.4s; }
    .arrow:nth-child(6) .pulse-dot { animation-delay: 0.8s; }
    .arrow:nth-child(8) .pulse-dot { animation-delay: 1.2s; }

    @keyframes pulse {
      0%, 100% { opacity: 0.3; }
      50% { opacity: 1; }
    }

    @media (max-width: 768px) {
      .pipeline {
        justify-content: flex-start;
        padding: 1.5rem 0;
      }
      .stage {
        min-width: 100px;
      }
      .icon-box {
        width: 48px;
        height: 48px;
        font-size: 1.25rem;
        border-radius: 12px;
      }
    }
  `;

  private _arrow() {
    return html`
      <div class="arrow">
        <svg viewBox="0 0 32 16" fill="none">
          <line x1="0" y1="8" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 3" />
          <circle class="pulse-dot" cx="26" cy="8" r="3" fill="currentColor" />
        </svg>
      </div>
    `;
  }

  override render() {
    return html`
      <div class="pipeline">
        <div class="stage">
          <div class="icon-box">API</div>
          <span class="label">Source APIs</span>
          <span class="sublabel">Garmin, Gmail, Spotify...</span>
        </div>
        ${this._arrow()}
        <div class="stage">
          <div class="icon-box">dlt</div>
          <span class="label">Extract + Load</span>
          <span class="sublabel">Incremental sync</span>
        </div>
        ${this._arrow()}
        <div class="stage">
          <div class="icon-box">DB</div>
          <span class="label">DuckDB</span>
          <span class="sublabel">Local storage</span>
        </div>
        ${this._arrow()}
        <div class="stage">
          <div class="icon-box">SQL</div>
          <span class="label">Transform</span>
          <span class="sublabel">Canonical schemas</span>
        </div>
        ${this._arrow()}
        <div class="stage">
          <div class="icon-box">ML</div>
          <span class="label">Federated ML</span>
          <span class="sublabel">Train locally, share gradients</span>
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-data-flow", DataFlow);
