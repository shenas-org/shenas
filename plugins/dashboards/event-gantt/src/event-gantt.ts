import { LitElement, html, css, nothing } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { query, arrowToRows, categoryColor, formatTime, formatDate, dayKey, computeBarPosition } from "shenas-frontends";
import type { EventItem } from "shenas-frontends";

interface DayGroup {
  date: Date;
  events: EventItem[];
}

export class ShenasEventGantt extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    days: { type: Number },
    _events: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _hoveredEvent: { state: true },
    _tooltipX: { state: true },
    _tooltipY: { state: true },
  };

  declare apiBase: string;
  declare days: number;
  declare _events: EventItem[];
  declare _loading: boolean;
  declare _error: string | null;
  declare _hoveredEvent: EventItem | null;
  declare _tooltipX: number;
  declare _tooltipY: number;

  static styles: CSSResult = css`
    :host {
      display: block;
      font-family: var(--shenas-font, system-ui, sans-serif);
      color: var(--shenas-text, #e8e8ef);
    }

    .container {
      overflow-x: auto;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    h2 {
      margin: 0;
      font-size: 1.2rem;
      font-weight: 600;
    }

    .controls {
      display: flex;
      gap: 0.5rem;
    }

    .controls button {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      color: var(--shenas-text, #e8e8ef);
      padding: 0.3rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
    }

    .controls button[aria-pressed="true"] {
      background: var(--shenas-accent, #6c5ce7);
      border-color: var(--shenas-accent, #6c5ce7);
    }

    .gantt-chart {
      margin-top: 1.5rem;
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 8px;
      background: var(--shenas-surface, #22222f);
    }

    .day-row {
      display: flex;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .day-row:last-child {
      border-bottom: none;
    }

    .day-label {
      padding: 0.75rem;
      background: var(--shenas-surface-alt, #2a2a3a);
      border-right: 1px solid var(--shenas-border, #2a2a3a);
      width: 100px;
      flex-shrink: 0;
      font-size: 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .day-date {
      font-weight: 600;
      color: var(--shenas-text-bright, #ffffff);
    }

    .day-time {
      font-size: 0.75rem;
      color: var(--shenas-text-muted, #a8a8c0);
    }

    .events-container {
      flex: 1;
      position: relative;
      padding: 0.5rem;
      height: 60px;
      overflow: hidden;
    }

    .event-bar {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      height: 24px;
      border-radius: 4px;
      padding: 0 0.5rem;
      display: flex;
      align-items: center;
      cursor: pointer;
      font-size: 0.75rem;
      font-weight: 500;
      color: white;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: opacity 0.2s, transform 0.2s;
    }

    .event-bar:hover {
      opacity: 0.9;
      transform: translateY(calc(-50% - 2px));
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    .tooltip {
      position: fixed;
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-accent, #6c5ce7);
      border-radius: 6px;
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
      z-index: 1000;
      pointer-events: none;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
    }

    .loading {
      text-align: center;
      padding: 2rem;
      color: var(--shenas-text-muted, #a8a8c0);
    }

    .error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;
      padding: 1rem;
      border-radius: 6px;
      margin-top: 1rem;
    }
  `;

  constructor() {
    super();
    this.apiBase = '';
    this.days = 7;
    this._events = [];
    this._loading = false;
    this._error = null;
    this._hoveredEvent = null;
    this._tooltipX = 0;
    this._tooltipY = 0;
  }

  connectedCallback() {
    super.connectedCallback();
    this.loadEvents();
  }

  private async loadEvents() {
    this._loading = true;
    this._error = null;

    try {
      const response = await fetch(`${this.apiBase}/api/metrics/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table: 'events.all_events',
          filters: [],
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this._events = arrowToRows(data);
    } catch (error) {
      this._error = error instanceof Error ? error.message : String(error);
    } finally {
      this._loading = false;
    }
  }

  private groupEventsByDay(): DayGroup[] {
    const groups: Map<string, EventItem[]> = new Map();

    for (const event of this._events) {
      const key = dayKey(new Date(event.time_start));
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(event);
    }

    return Array.from(groups.entries())
      .map(([key, events]) => ({
        date: new Date(key),
        events: events.sort(
          (a, b) =>
            new Date(a.time_start).getTime() -
            new Date(b.time_start).getTime()
        ),
      }))
      .sort((a, b) => a.date.getTime() - b.date.getTime());
  }

  private onEventHover(
    event: MouseEvent,
    item: EventItem
  ) {
    this._hoveredEvent = item;
    this._tooltipX = event.clientX;
    this._tooltipY = event.clientY;
  }

  private onEventLeave() {
    this._hoveredEvent = null;
  }

  render(): TemplateResult {
    if (this._loading) {
      return html`<div class="loading">Loading events...</div>`;
    }

    if (this._error) {
      return html`<div class="error">${this._error}</div>`;
    }

    const dayGroups = this.groupEventsByDay();

    return html`
      <div class="container">
        <div class="header">
          <h2>Events</h2>
          <div class="controls">
            <button @click=${() => this.loadEvents()}>Refresh</button>
          </div>
        </div>

        <div class="gantt-chart">
          ${dayGroups.map(
            (group) => html`
              <div class="day-row">
                <div class="day-label">
                  <span class="day-date">${formatDate(group.date)}</span>
                  <span class="day-time">${formatTime(group.date)}</span>
                </div>
                <div class="events-container">
                  ${group.events.map((event) => {
                    const position = computeBarPosition(
                      new Date(event.time_start),
                      new Date(event.time_end),
                      group.date
                    );

                    return html`
                      <div
                        class="event-bar"
                        style="left: ${position.left}%; width: ${position.width}%; background: ${categoryColor(
                          event.category
                        )}"
                        @mousemove=${(e: MouseEvent) =>
                          this.onEventHover(e, event)}
                        @mouseleave=${() => this.onEventLeave()}
                      >
                        ${event.name}
                      </div>
                    `;
                  })}
                </div>
              </div>
            `
          )}
        </div>
      </div>

      ${this._hoveredEvent
        ? html`
            <div
              class="tooltip"
              style="left: ${this._tooltipX}px; top: ${this._tooltipY}px"
            >
              <strong>${this._hoveredEvent.name}</strong>
              <div>${formatTime(new Date(this._hoveredEvent.time_start))} -
              ${formatTime(new Date(this._hoveredEvent.time_end))}</div>
              ${this._hoveredEvent.description
                ? html`<div>${this._hoveredEvent.description}</div>`
                : nothing}
            </div>
          `
        : nothing}
    `;
  }
}

customElements.define('shenas-event-gantt', ShenasEventGantt);
