import { LitElement, html, css, nothing } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { categoryColor, formatTime, formatDate, computeBarPosition } from "shenas-frontends";
import type { DayData, EventItem, TransactionItem, DailyMetrics } from "./types.ts";

function formatMetricValue(val: number | null | undefined, unit: string): string | null {
  if (val == null) return null;
  switch (unit) {
    case "sleep":
      return `${val.toFixed(1)}h`;
    case "hrv":
      return `${Math.round(val)}ms`;
    case "hr":
      return `${Math.round(val)}bpm`;
    case "steps":
      return val >= 1000 ? `${(val / 1000).toFixed(1)}k` : `${Math.round(val)}`;
    case "mood":
      return `${Math.round(val)}/9`;
    case "spent":
      return `$${Math.abs(val).toFixed(0)}`;
    case "weight":
      return `${val.toFixed(1)}kg`;
    default:
      return `${val}`;
  }
}

interface MetricBadge {
  label: string;
  value: string;
  color: string;
}

function buildBadges(m: DailyMetrics | null): MetricBadge[] {
  if (!m) return [];
  const badges: MetricBadge[] = [];
  const v = (val: number | null | undefined, unit: string, label: string, color: string): void => {
    const formatted = formatMetricValue(val, unit);
    if (formatted) badges.push({ label, value: formatted, color });
  };
  v(m.sleep_hours, "sleep", "sleep", "#a29bfe");
  v(m.rmssd, "hrv", "HRV", "#6c5ce7");
  v(m.resting_hr, "hr", "HR", "#e17055");
  v(m.steps, "steps", "steps", "#00b894");
  v(m.mood, "mood", "mood", "#fd79a8");
  v(m.total_spent, "spent", "spent", "#00cec9");
  return badges;
}

export class ShenasDayRow extends LitElement {
  static properties = {
    day: { type: Object },
    isToday: { type: Boolean, attribute: "is-today" },
    expanded: { type: Boolean },
    _hoveredItem: { state: true },
    _tooltipX: { state: true },
    _tooltipY: { state: true },
  };

  declare day: DayData;
  declare isToday: boolean;
  declare expanded: boolean;
  declare _hoveredItem: EventItem | TransactionItem | null;
  declare _tooltipX: number;
  declare _tooltipY: number;

  static styles: CSSResult = css`
    :host {
      display: block;
      font-family: var(--shenas-font, system-ui, sans-serif);
      color: var(--shenas-text, #e8e8ef);
    }

    .day-row {
      display: flex;
      align-items: stretch;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      min-height: 44px;
      cursor: pointer;
      transition: background 0.1s;
    }

    .day-row:hover {
      background: color-mix(in srgb, var(--shenas-accent, #6c5ce7) 5%, transparent);
    }

    .day-label {
      width: 90px;
      min-width: 90px;
      padding: 0.4rem 0.5rem;
      font-size: 0.78rem;
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

    .metrics-sidebar {
      width: 200px;
      min-width: 200px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 3px;
      padding: 3px 6px;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 0.65rem;
      white-space: nowrap;
      background: color-mix(in srgb, var(--bg) 15%, transparent);
      color: var(--shenas-text-secondary, #bbb);
    }

    .badge .label {
      font-weight: 500;
      opacity: 0.7;
    }

    .badge .value {
      font-weight: 600;
    }

    .timeline {
      flex: 1;
      display: flex;
      align-items: center;
      position: relative;
      overflow: hidden;
      gap: 2px;
      padding: 2px 4px;
    }

    .timeline-item {
      height: 32px;
      border-radius: 2px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.7rem;
      font-weight: 600;
      color: white;
      cursor: pointer;
      transition: transform 0.15s;
      white-space: nowrap;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
      min-width: 24px;
    }

    .timeline-item:hover {
      transform: scale(1.05);
    }

    .timeline-item.event {
      background: var(--event-color, #6c5ce7);
    }

    .timeline-item.transaction {
      background: var(--tx-color, #00cec9);
    }

    .tooltip {
      position: fixed;
      background: var(--shenas-bg-modal, #1a1a28);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 4px;
      padding: 6px 8px;
      font-size: 0.75rem;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      pointer-events: none;
    }

    .tooltip .title {
      font-weight: 600;
      margin-bottom: 2px;
    }

    .tooltip .detail {
      color: var(--shenas-text-secondary, #bbb);
      font-size: 0.7rem;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._hoveredItem = null;
    this._tooltipX = 0;
    this._tooltipY = 0;
  }

  _onItemHover(item: EventItem | TransactionItem, e: MouseEvent): void {
    this._hoveredItem = item;
    this._tooltipX = e.clientX + 10;
    this._tooltipY = e.clientY + 10;
  }

  _onItemLeave(): void {
    this._hoveredItem = null;
  }

  render(): TemplateResult {
    const d = this.day;
    const badges = buildBadges(d.metrics || null);
    const allItems = [...(d.events || []), ...(d.transactions || [])];

    return html`
      <div class="day-row">
        <div class="day-label ${this.isToday ? "today" : ""}">${formatDate(d.date)}</div>
        <div class="metrics-sidebar">
          ${badges.map(
            (b) =>
              html`<div class="badge" style="--bg: ${b.color}">
                <span class="label">${b.label}</span>
                <span class="value">${b.value}</span>
              </div>`,
          )}
        </div>
        <div class="timeline">
          ${allItems.map((item) => {
            const isEvent = "title" in item;
            return html`
              <div
                class="timeline-item ${isEvent ? "event" : "transaction"}"
                style="${computeBarPosition(item.start_time, item.end_time || item.start_time, d.date)}"
                @mouseenter=${(e: MouseEvent) => this._onItemHover(item, e)}
                @mouseleave=${() => this._onItemLeave()}
              >
                ${isEvent ? (item as EventItem).title.substring(0, 3) : "$"}
              </div>
            `;
          })}
        </div>
      </div>
      ${this._hoveredItem
        ? html`<div
            class="tooltip"
            style="left: ${this._tooltipX}px; top: ${this._tooltipY}px"
          >
            <div class="title">${"title" in this._hoveredItem ? this._hoveredItem.title : "Transaction"}</div>
            <div class="detail">
              ${"title" in this._hoveredItem
                ? html`${formatTime(this._hoveredItem.start_time)} - ${formatTime(this._hoveredItem.end_time || this._hoveredItem.start_time)}`
                : html`${this._hoveredItem.amount ? `$${Math.abs(this._hoveredItem.amount).toFixed(2)}` : "N/A"}`}
            </div>
          </div>`
        : nothing}
    `;
  }
}

customElements.define("shenas-day-row", ShenasDayRow);
