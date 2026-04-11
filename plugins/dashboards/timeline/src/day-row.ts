import { LitElement, html, css, nothing } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import type { DayData, EventItem, TransactionItem, DailyMetrics } from "./types.ts";

const CATEGORY_COLORS: Record<string, string> = {
  meeting: "#6c5ce7",
  workout: "#00b894",
  running: "#00b894",
  cycling: "#00b894",
  swimming: "#00b894",
  music: "#e17055",
  meal: "#fdcb6e",
  focus: "#0984e3",
  sleep: "#a29bfe",
  finance: "#00cec9",
  social: "#fd79a8",
  travel: "#ffeaa7",
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
  return date.toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

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
      color: var(--bg);
    }

    .badge-label {
      opacity: 0.7;
    }

    .timeline {
      flex: 1;
      position: relative;
      min-height: 40px;
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

    .all-day-bar {
      position: relative;
      height: 16px;
      margin: 1px 2px;
      border-radius: 3px;
      display: flex;
      align-items: center;
      padding: 0 4px;
      opacity: 0.6;
    }

    .all-day-bar .bar-label {
      font-size: 0.6rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: white;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
    }

    .transaction-dot {
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%) rotate(45deg);
      width: 6px;
      height: 6px;
      background: var(--shenas-accent, #00cec9);
      cursor: pointer;
      z-index: 5;
    }

    .transaction-dot:hover {
      transform: translate(-50%, -50%) rotate(45deg) scale(1.4);
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

    /* ---- Expanded day view ---- */

    .expanded-view {
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .expanded-header {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .expanded-header h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
    }

    .expanded-header .back-btn {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      color: var(--shenas-text, #e8e8ef);
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.75rem;
    }

    .expanded-metrics {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .metric-card {
      background: var(--shenas-surface, #22222f);
      border: 1px solid var(--shenas-border, #2a2a3a);
      border-radius: 6px;
      padding: 0.4rem 0.6rem;
      min-width: 80px;
    }

    .metric-card .metric-label {
      font-size: 0.65rem;
      color: var(--shenas-text-muted, #8888a0);
      text-transform: uppercase;
    }

    .metric-card .metric-value {
      font-size: 1rem;
      font-weight: 600;
    }

    .swim-lanes {
      padding: 0.5rem 0;
    }

    .lane {
      display: flex;
      align-items: stretch;
      min-height: 32px;
      border-bottom: 1px solid color-mix(in srgb, var(--shenas-border, #2a2a3a) 50%, transparent);
    }

    .lane-label {
      width: 90px;
      min-width: 90px;
      padding: 0.25rem 0.5rem;
      font-size: 0.7rem;
      color: var(--shenas-text-muted, #8888a0);
      display: flex;
      align-items: center;
      border-right: 1px solid var(--shenas-border, #2a2a3a);
    }

    .lane-timeline {
      flex: 1;
      position: relative;
      min-height: 28px;
      padding: 2px 0;
    }

    .hour-labels {
      display: flex;
      padding-left: 90px;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
    }

    .hour-label {
      flex: 1;
      font-size: 0.6rem;
      color: var(--shenas-text-muted, #8888a0);
      text-align: center;
      padding: 0.15rem 0;
    }

    .transactions-list {
      padding: 0.5rem 1rem;
    }

    .transactions-list h4 {
      margin: 0 0 0.4rem 0;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--shenas-text-muted, #8888a0);
    }

    .tx-row {
      display: flex;
      gap: 1rem;
      padding: 0.25rem 0;
      font-size: 0.78rem;
      border-bottom: 1px solid color-mix(in srgb, var(--shenas-border, #2a2a3a) 30%, transparent);
    }

    .tx-payee {
      flex: 1;
    }

    .tx-category {
      color: var(--shenas-text-muted, #8888a0);
      min-width: 100px;
    }

    .tx-amount {
      min-width: 70px;
      text-align: right;
      font-weight: 500;
    }

    .tx-amount.expense {
      color: #e74c3c;
    }

    .tx-amount.income {
      color: #00b894;
    }
  `;

  constructor() {
    super();
    this.day = { date: new Date(), dateKey: "", items: [], metrics: null };
    this.isToday = false;
    this.expanded = false;
    this._hoveredItem = null;
    this._tooltipX = 0;
    this._tooltipY = 0;
  }

  _onItemEnter(item: EventItem | TransactionItem, e: MouseEvent): void {
    e.stopPropagation();
    this._hoveredItem = item;
    this._tooltipX = e.clientX + 12;
    this._tooltipY = e.clientY - 10;
  }

  _onItemMove(e: MouseEvent): void {
    this._tooltipX = e.clientX + 12;
    this._tooltipY = e.clientY - 10;
  }

  _onItemLeave(): void {
    this._hoveredItem = null;
  }

  _onRowClick(): void {
    this.dispatchEvent(
      new CustomEvent("day-click", {
        bubbles: true,
        composed: true,
        detail: { dateKey: this.day.dateKey },
      }),
    );
  }

  _onBackClick(e: MouseEvent): void {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent("day-back", {
        bubbles: true,
        composed: true,
      }),
    );
  }

  render(): TemplateResult {
    if (this.expanded) return this._renderExpanded();
    return this._renderCompact();
  }

  _renderCompact(): TemplateResult {
    const events = this.day.items.filter((i) => i.type === "event") as EventItem[];
    const transactions = this.day.items.filter((i) => i.type === "transaction") as TransactionItem[];
    const badges = buildBadges(this.day.metrics);
    const allDayEvents = events.filter((e) => e.all_day);
    const timedEvents = events.filter((e) => !e.all_day);

    return html`
      <div class="day-row" @click=${this._onRowClick}>
        <div class="day-label ${this.isToday ? "today" : ""}">${formatDate(this.day.date)}</div>
        <div class="metrics-sidebar">
          ${badges.map(
            (b) => html`
              <span class="badge" style="--bg: ${b.color}">
                <span class="badge-label">${b.label}</span> ${b.value}
              </span>
            `,
          )}
        </div>
        <div class="timeline">
          <div class="hour-grid">${Array.from({ length: 24 }, () => html`<div class="hour-line"></div>`)}</div>
          ${allDayEvents.map((ev) => this._renderAllDayBar(ev))} ${timedEvents.map((ev) => this._renderEventBar(ev))}
          ${transactions.map((tx, i) => this._renderTransactionDot(tx, i, transactions.length))}
        </div>
      </div>
      ${this._renderTooltip()}
    `;
  }

  _renderExpanded(): TemplateResult {
    const events = this.day.items.filter((i) => i.type === "event") as EventItem[];
    const transactions = this.day.items.filter((i) => i.type === "transaction") as TransactionItem[];
    const m = this.day.metrics;

    // Group events by source for swim lanes
    const laneMap = new Map<string, EventItem[]>();
    for (const ev of events) {
      const src = ev.source || "other";
      if (!laneMap.has(src)) laneMap.set(src, []);
      laneMap.get(src)!.push(ev);
    }

    return html`
      <div class="expanded-view">
        <div class="expanded-header">
          <button class="back-btn" @click=${this._onBackClick}>Back</button>
          <h3>${formatDate(this.day.date)}</h3>
        </div>

        ${m ? this._renderMetricsPanel(m) : nothing}

        <div class="hour-labels">
          ${Array.from(
            { length: 24 },
            (_, i) =>
              html`<div class="hour-label">
                ${i === 0 ? "12a" : i < 12 ? `${i}a` : i === 12 ? "12p" : `${i - 12}p`}
              </div>`,
          )}
        </div>

        <div class="swim-lanes">
          ${[...laneMap.entries()].map(
            ([src, evs]) => html`
              <div class="lane">
                <div class="lane-label">${src}</div>
                <div class="lane-timeline">
                  <div class="hour-grid">${Array.from({ length: 24 }, () => html`<div class="hour-line"></div>`)}</div>
                  ${evs.map((ev) => (ev.all_day ? this._renderAllDayBar(ev) : this._renderEventBar(ev)))}
                </div>
              </div>
            `,
          )}
        </div>

        ${transactions.length > 0
          ? html`
              <div class="transactions-list">
                <h4>Transactions (${transactions.length})</h4>
                ${transactions.map(
                  (tx) => html`
                    <div class="tx-row">
                      <span class="tx-payee">${tx.payee || "Unknown"}</span>
                      <span class="tx-category">${tx.category || ""}</span>
                      <span class="tx-amount ${(tx.amount ?? 0) >= 0 ? "income" : "expense"}">
                        ${(tx.amount ?? 0) >= 0 ? "+" : ""}${(tx.amount ?? 0).toFixed(2)}
                      </span>
                    </div>
                  `,
                )}
              </div>
            `
          : nothing}
      </div>
      ${this._renderTooltip()}
    `;
  }

  _renderMetricsPanel(m: DailyMetrics): TemplateResult {
    interface MetricDef {
      key: keyof DailyMetrics;
      label: string;
      unit: string;
      color: string;
    }
    const defs: MetricDef[] = [
      { key: "sleep_hours", label: "Sleep", unit: "sleep", color: "#a29bfe" },
      { key: "sleep_score", label: "Sleep Score", unit: "mood", color: "#a29bfe" },
      { key: "rmssd", label: "HRV", unit: "hrv", color: "#6c5ce7" },
      { key: "resting_hr", label: "Resting HR", unit: "hr", color: "#e17055" },
      { key: "steps", label: "Steps", unit: "steps", color: "#00b894" },
      { key: "active_kcal", label: "Active Cal", unit: "steps", color: "#00b894" },
      { key: "mood", label: "Mood", unit: "mood", color: "#fd79a8" },
      { key: "stress", label: "Stress", unit: "mood", color: "#e17055" },
      { key: "productivity", label: "Productivity", unit: "mood", color: "#0984e3" },
      { key: "total_spent", label: "Spent", unit: "spent", color: "#00cec9" },
      { key: "weight_kg", label: "Weight", unit: "weight", color: "#636e72" },
    ];

    const visible = defs.filter((d) => m[d.key] != null);
    if (visible.length === 0) return html``;

    return html`
      <div class="expanded-metrics">
        ${visible.map((d) => {
          const formatted = formatMetricValue(m[d.key] as number, d.unit);
          return html`
            <div class="metric-card">
              <div class="metric-label">${d.label}</div>
              <div class="metric-value" style="color: ${d.color}">${formatted}</div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderEventBar(ev: EventItem): TemplateResult {
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
        @mouseenter=${(e: MouseEvent) => this._onItemEnter(ev, e)}
        @mousemove=${(e: MouseEvent) => this._onItemMove(e)}
        @mouseleave=${() => this._onItemLeave()}
      >
        ${showLabel ? html`<span class="bar-label">${ev.title || ""}</span>` : nothing}
      </div>
    `;
  }

  _renderAllDayBar(ev: EventItem): TemplateResult {
    const color = categoryColor(ev.category);
    return html`
      <div
        class="all-day-bar"
        style="background: ${color}"
        @mouseenter=${(e: MouseEvent) => this._onItemEnter(ev, e)}
        @mousemove=${(e: MouseEvent) => this._onItemMove(e)}
        @mouseleave=${() => this._onItemLeave()}
      >
        <span class="bar-label">${ev.title || "All day"}</span>
      </div>
    `;
  }

  _renderTransactionDot(tx: TransactionItem, idx: number, total: number): TemplateResult {
    // Spread transaction dots across the first hour to avoid overlap
    const offset = total > 1 ? (idx / (total - 1)) * 4 : 0;
    const leftPct = offset;
    return html`
      <div
        class="transaction-dot"
        style="left: ${leftPct}%"
        @mouseenter=${(e: MouseEvent) => this._onItemEnter(tx, e)}
        @mousemove=${(e: MouseEvent) => this._onItemMove(e)}
        @mouseleave=${() => this._onItemLeave()}
      ></div>
    `;
  }

  _renderTooltip(): TemplateResult | typeof nothing {
    if (!this._hoveredItem) return nothing;
    const item = this._hoveredItem;

    if (item.type === "event") {
      const ev = item as EventItem;
      return html`
        <div class="tooltip" style="left: ${this._tooltipX}px; top: ${this._tooltipY}px">
          <div class="tooltip-title">${ev.title || "Untitled"}</div>
          <div class="tooltip-meta">
            <span>${ev._start ? formatTime(ev._start) : ""}${ev._end ? ` - ${formatTime(ev._end)}` : ""}</span>
            <span>${ev.category || "uncategorized"} / ${ev.source}</span>
            ${ev.location ? html`<span>${ev.location}</span>` : nothing}
            ${ev.duration_min ? html`<span>${Math.round(ev.duration_min)} min</span>` : nothing}
          </div>
        </div>
      `;
    }

    const tx = item as TransactionItem;
    return html`
      <div class="tooltip" style="left: ${this._tooltipX}px; top: ${this._tooltipY}px">
        <div class="tooltip-title">${tx.payee || "Transaction"}</div>
        <div class="tooltip-meta">
          <span>${tx.category || "uncategorized"}</span>
          ${tx.amount != null ? html`<span>${tx.amount >= 0 ? "+" : ""}${tx.amount.toFixed(2)}</span>` : nothing}
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-day-row", ShenasDayRow);
