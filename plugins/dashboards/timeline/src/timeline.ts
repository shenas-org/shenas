import { LitElement, html, css, nothing } from "lit";
import type { TemplateResult } from "lit";
import "shenas-frontends";
import "./day-row.ts";
import type { DayData } from "./types.ts";

interface Message {
  type: string;
  text: string;
}

export class ShenasTimeline extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _days: { state: true },
    _loading: { state: true },
    _message: { state: true },
    _expandedDay: { state: true },
  };

  declare apiBase: string;
  declare _days: DayData[];
  declare _loading: boolean;
  declare _message: Message | null;
  declare _expandedDay: string | null;

  static styles = [
    css`
      :host {
        display: block;
        font-family: var(--shenas-font, system-ui, sans-serif);
        color: var(--shenas-text, #e8e8ef);
        background: var(--shenas-bg, #0f0f1a);
        padding: 1rem;
      }

      .timeline-container {
        max-width: 1200px;
        margin: 0 auto;
      }

      .timeline-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      }

      .timeline-header h1 {
        margin: 0;
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--shenas-text, #e8e8ef);
      }

      .timeline-body {
        display: flex;
        flex-direction: column;
        gap: 0;
      }

      .timeline-item:last-child {
        border-bottom: none;
      }

      .loading-state {
        padding: 2rem 1rem;
        text-align: center;
        color: var(--shenas-text-secondary, #bbb);
      }

      .empty-state {
        padding: 2rem 1rem;
        text-align: center;
        color: var(--shenas-text-secondary, #bbb);
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "/api";
    this._days = [];
    this._loading = true;
    this._message = null;
    this._expandedDay = null;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchTimeline();
  }

  async _fetchTimeline(): Promise<void> {
    this._loading = true;
    try {
      const resp = await fetch(`${this.apiBase}/graphql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: `{ timeline { date dateKey items { ... on EventItem { type title start_at end_at category } ... on TransactionItem { type amount payee category } } metrics { sleep_hours rmssd resting_hr steps mood total_spent } } }`,
        }),
      });
      const json = await resp.json();
      this._days = json?.data?.timeline || [];
    } catch (err) {
      this._message = { type: "error", text: "Failed to fetch timeline" };
      console.error(err);
    } finally {
      this._loading = false;
    }
  }

  _toggleDay(date: string): void {
    this._expandedDay = this._expandedDay === date ? null : date;
  }

  render(): TemplateResult {
    if (this._loading) {
      return html`
        <div class="timeline-container">
          ${this._message ? html`<div class="message ${this._message.type}">${this._message.text}</div>` : nothing}
          <div class="loading-state">Loading timeline...</div>
        </div>
      `;
    }

    if (!this._days || this._days.length === 0) {
      return html`
        <div class="timeline-container">
          ${this._message ? html`<div class="message ${this._message.type}">${this._message.text}</div>` : nothing}
          <div class="empty-state">No data available</div>
        </div>
      `;
    }

    const today = new Date().toISOString().split("T")[0];

    return html`
      <div class="timeline-container">
        ${this._message ? html`<div class="message ${this._message.type}">${this._message.text}</div>` : nothing}
        <div class="timeline-header">
          <h1>Timeline</h1>
        </div>
        <div class="timeline-body">
          ${this._days.map((day) => {
            const isToday = day.dateKey === today;
            return html`
              <shenas-day-row
                .day=${day}
                ?is-today=${isToday}
                ?expanded=${this._expandedDay === day.dateKey}
                @click=${() => this._toggleDay(day.dateKey)}
              ></shenas-day-row>
            `;
          })}
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-timeline", ShenasTimeline);
