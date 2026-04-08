import { LitElement, html, css, nothing } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { query, arrowToRows } from "./arrow-client.ts";
import type { RowData } from "./arrow-client.ts";

interface EventData extends RowData {
  source?: string;
  source_id?: string;
  start_at?: bigint | number;
  end_at?: bigint | number;
  duration_min?: number;
  title?: string;
  category?: string;
  _start?: Date;
  _end?: Date;
}

interface DayGroup {
  date: Date;
  events: EventData[];
}

const CATEGORY_COLORS: Record<string, string> = {
  meeting: "#6c5ce7",
  workout: "#00b894",
  running: "#00b894",
  music: "#e17055",
  meal: "#fdcb6e",
  focus: "#0984e3",
  default: "#636e72",
};

export function categoryColor(cat: string | undefined): string {
  if (!cat) return CATEGORY_COLORS.default;
  const key = cat.toLowerCase();
  return CATEGORY_COLORS[key] || CATEGORY_COLORS.default;
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
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
  declare _events: EventData[];
  declare _loading: boolean;
  declare _error: string | null;
  declare _hoveredEvent: EventData | null;
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
      color: white;
    }

    .loading,
    .error,
    .empty {
      padding: 2rem;
      text-align: center;
      color: var(--shenas-text-muted, #8888a0);
    }

    .error {
      color: #e74c3c;
    }

    .gantt {
      min-width: 100%;
    }

    .day-row {
      display: flex;
      align-items: stretch;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      min-height: 36px;
    }

    .day-label {
      width: 120px;
      min-width: 120px;
      padding: 0.4rem 0.75rem;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--shenas-text-muted, #8888a0);
      display: flex;
      align-items: center;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
    }

    .day-label.today {
      color: var(--shenas-accent, #6c5ce7);
      font-weight: 600;
    }

    .timeline {
      flex: 1;
      position: relative;
      min-height: 32px;
      padding: 2px 0;
    }

    .hour-grid {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
    }

    .hour-line {
      flex: 1;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
      opacity: 0.3;
    }

    .hour-line:last-child {
      border-right: none;
    }

    .event-bar {
      position: absolute;
      top: 3px;
      height: calc(100% - 6px);
      min-width: 3px;
      border-radius: 3px;
      cursor: pointer;
      opacity: 0.85;
      transition: opacity 0.15s;
      display: flex;
      align-items: center;
      padding: 0 4px;
      overflow: hidden;
    }

    .event-bar:hover {
      opacity: 1;
      z-index: 10;
    }

    .event-bar .bar-label {
      font-size: 0.65rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: white;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
    }

    .hour-labels {
      display: flex;
      padding-left: 120px;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      margin-bottom: 2px;
    }

    .hour-label {
      flex: 1;
      font-size: 0.65rem;
      color: var(--shenas-text-muted, #8888a0);
      text-align: center;
      padding: 0.2rem 0;
    }

    .legend {
      display: flex;
      gap: 1rem;
      margin-top: 0.75rem;
      flex-wrap: wrap;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      color: var(--shenas-text-muted, #8888a0);
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 2px;
    }

    .tooltip {
      position: fixed;
      background: var(--shenas-bg-card, #1a1a25);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 8px;
      padding: 0.6rem 0.8rem;
      font-size: 0.8rem;
      z-index: 1000;
      pointer-events: none;
      max-width: 300px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }

    .tooltip-title {
      font-weight: 600;
      margin-bottom: 0.3rem;
    }

    .tooltip-meta {
      color: var(--shenas-text-muted, #8888a0);
      font-size: 0.75rem;
    }

    .tooltip-meta span {
      display: block;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this.days = 7;
    this._events = [];
    this._loading = false;
    this._error = null;
    this._hoveredEvent = null;
    this._tooltipX = 0;
    this._tooltipY = 0;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchEvents();
  }

  async _fetchEvents(): Promise<void> {
    this._loading = true;
    this._error = null;
    try {
      const table = await query(
        this.apiBase,
        `SELECT source, source_id, start_at, end_at, duration_min, title, category
         FROM metrics.events
         WHERE start_at >= current_date - INTERVAL '${this.days}' DAY
         ORDER BY start_at`,
      );
      this._events = arrowToRows(table) as EventData[];
    } catch (e) {
      this._error = (e as Error).message;
    }
    this._loading = false;
  }

  _setDays(n: number): void {
    this.days = n;
    this._fetchEvents();
  }

  _groupByDay(): DayGroup[] {
    const groups = new Map<string, DayGroup>();
    for (const ev of this._events) {
      const start = new Date(Number(ev.start_at) / 1000);
      const key = dayKey(start);
      if (!groups.has(key)) groups.set(key, { date: start, events: [] });
      groups.get(key)!.events.push({ ...ev, _start: start });
    }
    return [...groups.values()].sort((a, b) => a.date.getTime() - b.date.getTime());
  }

  _onBarEnter(ev: EventData, e: MouseEvent): void {
    this._hoveredEvent = ev;
    this._tooltipX = e.clientX + 12;
    this._tooltipY = e.clientY - 10;
  }

  _onBarMove(e: MouseEvent): void {
    this._tooltipX = e.clientX + 12;
    this._tooltipY = e.clientY - 10;
  }

  _onBarLeave(): void {
    this._hoveredEvent = null;
  }

  render(): TemplateResult {
    if (this._loading) return html`<div class="loading">Loading events...</div>`;
    if (this._error) return html`<div class="error">${this._error}</div>`;
    if (this._events.length === 0) return html`<div class="empty">No events in the last ${this.days} days.</div>`;

    const days = this._groupByDay();
    const todayStr = dayKey(new Date());
    const categories = [...new Set(this._events.map((e) => e.category).filter(Boolean))] as string[];

    return html`
      <div class="header">
        <h2>Events Timeline</h2>
        <div class="controls">
          ${[7, 14, 30].map(
            (n) => html`<button aria-pressed=${this.days === n} @click=${() => this._setDays(n)}>${n}d</button>`,
          )}
        </div>
      </div>

      <div class="container">
        <div class="gantt">
          <div class="hour-labels">
            ${Array.from(
              { length: 24 },
              (_, i) =>
                html`<div class="hour-label">
                  ${i === 0 ? "12a" : i < 12 ? `${i}a` : i === 12 ? "12p" : `${i - 12}p`}
                </div>`,
            )}
          </div>

          ${days.map(({ date, events }) => {
            const key = dayKey(date);
            const isToday = key === todayStr;
            return html`
              <div class="day-row">
                <div class="day-label ${isToday ? "today" : ""}">${formatDate(date)}</div>
                <div class="timeline">
                  <div class="hour-grid">${Array.from({ length: 24 }, () => html`<div class="hour-line"></div>`)}</div>
                  ${events.map((ev) => this._renderBar(ev))}
                </div>
              </div>
            `;
          })}
        </div>
      </div>

      <div class="legend">
        ${categories.map(
          (cat) => html`
            <div class="legend-item">
              <div class="legend-dot" style="background: ${categoryColor(cat)}"></div>
              ${cat}
            </div>
          `,
        )}
      </div>

      ${this._hoveredEvent
        ? html`
            <div class="tooltip" style="left: ${this._tooltipX}px; top: ${this._tooltipY}px">
              <div class="tooltip-title">${this._hoveredEvent.title || "Untitled"}</div>
              <div class="tooltip-meta">
                <span
                  >${formatTime(this._hoveredEvent._start!)}${this._hoveredEvent._end
                    ? ` - ${formatTime(this._hoveredEvent._end)}`
                    : ""}</span
                >
                <span>${this._hoveredEvent.category || "uncategorized"} / ${this._hoveredEvent.source}</span>
                ${this._hoveredEvent.duration_min
                  ? html`<span>${Math.round(this._hoveredEvent.duration_min)} min</span>`
                  : nothing}
              </div>
            </div>
          `
        : nothing}
    `;
  }

  _renderBar(ev: EventData): TemplateResult {
    const hours = ev._start!.getHours() + ev._start!.getMinutes() / 60;
    const leftPct = (hours / 24) * 100;
    let durationHours = ((ev.duration_min as number) || 30) / 60;
    if (ev.end_at) {
      const end = new Date(Number(ev.end_at) / 1000);
      durationHours = (end.getTime() - ev._start!.getTime()) / 3600000;
      ev._end = end;
    }
    const widthPct = Math.max((durationHours / 24) * 100, 0.3);
    const color = categoryColor(ev.category);
    const showLabel = widthPct > 4;

    return html`
      <div
        class="event-bar"
        style="left: ${leftPct}%; width: ${widthPct}%; background: ${color}"
        @mouseenter=${(e: MouseEvent) => this._onBarEnter(ev, e)}
        @mousemove=${(e: MouseEvent) => this._onBarMove(e)}
        @mouseleave=${() => this._onBarLeave()}
      >
        ${showLabel ? html`<span class="bar-label">${ev.title || ""}</span>` : nothing}
      </div>
    `;
  }
}

customElements.define("shenas-event-gantt", ShenasEventGantt);
