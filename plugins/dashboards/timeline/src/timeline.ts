import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";
import { query, arrowToRows } from "shenas-frontends";
import type { RowData } from "shenas-frontends";
import { dayKey, categoryColor } from "./day-row.ts";
import "./day-row.ts";
import type { DayData, EventItem, TransactionItem, DailyMetrics } from "./types.ts";

function addDays(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function toISODate(date: Date): string {
  return dayKey(date);
}

function parseArrowTimestamp(val: bigint | number | undefined | null): Date | null {
  if (val == null) return null;
  // Arrow timestamps come as microseconds since epoch
  return new Date(Number(val) / 1000);
}

export class ShenasTimeline extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _centerDate: { state: true },
    _days: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _expandedDay: { state: true },
  };

  declare apiBase: string;
  declare _centerDate: Date;
  declare _days: DayData[];
  declare _loading: boolean;
  declare _error: string | null;
  declare _expandedDay: string | null;

  static styles: CSSResult = css`
    :host {
      display: block;
      font-family: var(--shenas-font, system-ui, sans-serif);
      color: var(--shenas-text, #e8e8ef);
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    h2 {
      margin: 0;
      font-size: 1.2rem;
      font-weight: 600;
    }

    .nav {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .nav button,
    .nav input[type="date"] {
      background: var(--shenas-bg-secondary, #f3f0eb);
      border: 1px solid var(--shenas-border, #d8d4cc);
      color: var(--shenas-text, #2c2c28);
      padding: 0.3rem 0.6rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
    }

    .nav button:hover {
      background: var(--shenas-bg-hover, #edeae4);
      border-color: var(--shenas-border, #d8d4cc);
    }

    .nav input[type="date"] {
      cursor: text;
    }

    .nav input[type="date"]::-webkit-calendar-picker-indicator {
      filter: invert(0.7);
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

    .hour-labels {
      display: flex;
      padding-left: 290px;
      border-bottom: 1px solid var(--shenas-border, #2a2a3a);
      margin-bottom: 2px;
    }

    .hour-label {
      flex: 1;
      font-size: 0.6rem;
      color: var(--shenas-text-muted, #8888a0);
      text-align: center;
      padding: 0.15rem 0;
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
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._centerDate = new Date();
    this._days = [];
    this._loading = false;
    this._error = null;
    this._expandedDay = null;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchData();
    this.addEventListener("keydown", this._onKeyDown.bind(this) as EventListener);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.removeEventListener("keydown", this._onKeyDown.bind(this) as EventListener);
  }

  _onKeyDown(e: KeyboardEvent): void {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      this._navigate(this._expandedDay ? -1 : -7);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      this._navigate(this._expandedDay ? 1 : 7);
    } else if (e.key === "Escape" && this._expandedDay) {
      e.preventDefault();
      this._expandedDay = null;
    }
  }

  _navigate(days: number): void {
    this._centerDate = addDays(this._centerDate, days);
    this._fetchData();
  }

  _goToday(): void {
    this._centerDate = new Date();
    this._expandedDay = null;
    this._fetchData();
  }

  _onDateInput(e: Event): void {
    const val = (e.target as HTMLInputElement).value;
    if (!val) return;
    const [y, m, d] = val.split("-").map(Number);
    this._centerDate = new Date(y, m - 1, d);
    this._fetchData();
  }

  _onDayClick(e: CustomEvent): void {
    this._expandedDay = e.detail.dateKey;
  }

  _onDayBack(): void {
    this._expandedDay = null;
  }

  get _windowStart(): Date {
    return addDays(this._centerDate, -6);
  }

  get _windowEnd(): Date {
    return addDays(this._centerDate, 1);
  }

  async _fetchData(): Promise<void> {
    this._loading = true;
    this._error = null;
    const start = toISODate(this._windowStart);
    const end = toISODate(this._windowEnd);

    try {
      const [eventsTable, txTable, metricsTable] = await Promise.all([
        query(
          this.apiBase,
          `SELECT source, source_id, start_at, end_at, duration_min, title, category, location, all_day
           FROM metrics.events
           WHERE start_at >= '${start}' AND start_at < '${end}'
           ORDER BY start_at`,
        ).catch(() => null),
        query(
          this.apiBase,
          `SELECT date, amount, payee, category, category_group
           FROM metrics.transactions
           WHERE date >= '${start}' AND date < '${end}'
           ORDER BY date`,
        ).catch(() => null),
        query(
          this.apiBase,
          `SELECT
             COALESCE(s.date, v.date, h.date, o.date, sp.date, b.date) AS date,
             s.total_hours AS sleep_hours, s.score AS sleep_score,
             h.rmssd,
             v.resting_hr, v.steps, v.active_kcal,
             o.mood, o.stress, o.productivity,
             sp.total_spent, sp.transaction_count,
             b.weight_kg
           FROM metrics.daily_sleep s
           FULL OUTER JOIN metrics.daily_vitals v USING (date)
           FULL OUTER JOIN metrics.daily_hrv h USING (date)
           FULL OUTER JOIN metrics.daily_outcomes o USING (date)
           FULL OUTER JOIN metrics.daily_spending sp USING (date)
           FULL OUTER JOIN metrics.daily_body b USING (date)
           WHERE COALESCE(s.date, v.date, h.date, o.date, sp.date, b.date) >= '${start}'
             AND COALESCE(s.date, v.date, h.date, o.date, sp.date, b.date) < '${end}'
           ORDER BY date`,
        ).catch(() => null),
      ]);

      // Parse events
      const events: EventItem[] = eventsTable
        ? (arrowToRows(eventsTable) as RowData[]).map((r) => {
            const startDate = parseArrowTimestamp(r.start_at as bigint | number);
            const endDate = parseArrowTimestamp(r.end_at as bigint | number);
            return {
              type: "event" as const,
              source: r.source as string | undefined,
              source_id: r.source_id as string | undefined,
              start_at: r.start_at as bigint | number | undefined,
              end_at: r.end_at as bigint | number | undefined,
              duration_min: r.duration_min as number | undefined,
              title: r.title as string | undefined,
              category: r.category as string | undefined,
              location: r.location as string | undefined,
              all_day: r.all_day as boolean | undefined,
              _start: startDate ?? undefined,
              _end: endDate ?? undefined,
            };
          })
        : [];

      // Parse transactions
      const transactions: TransactionItem[] = txTable
        ? (arrowToRows(txTable) as RowData[]).map((r) => ({
            type: "transaction" as const,
            date: String(r.date ?? ""),
            amount: r.amount as number | undefined,
            payee: r.payee as string | undefined,
            category: r.category as string | undefined,
            category_group: r.category_group as string | undefined,
          }))
        : [];

      // Parse daily metrics into a map by date key
      const metricsMap = new Map<string, DailyMetrics>();
      if (metricsTable) {
        for (const r of arrowToRows(metricsTable) as RowData[]) {
          const dk = String(r.date ?? "");
          metricsMap.set(dk, {
            sleep_hours: r.sleep_hours as number | null,
            sleep_score: r.sleep_score as number | null,
            rmssd: r.rmssd as number | null,
            resting_hr: r.resting_hr as number | null,
            steps: r.steps as number | null,
            active_kcal: r.active_kcal as number | null,
            mood: r.mood as number | null,
            stress: r.stress as number | null,
            productivity: r.productivity as number | null,
            total_spent: r.total_spent as number | null,
            transaction_count: r.transaction_count as number | null,
            weight_kg: r.weight_kg as number | null,
          });
        }
      }

      // Build day data for each day in the window
      const days: DayData[] = [];
      let cursor = new Date(this._windowStart);
      while (cursor <= this._centerDate) {
        const dk = dayKey(cursor);
        const dayEvents = events.filter((e) => e._start && dayKey(e._start) === dk);
        const dayTx = transactions.filter((t) => t.date === dk);
        days.push({
          date: new Date(cursor),
          dateKey: dk,
          items: [...dayEvents, ...dayTx],
          metrics: metricsMap.get(dk) ?? null,
        });
        cursor = addDays(cursor, 1);
      }
      this._days = days;
    } catch (e) {
      this._error = (e as Error).message;
    }
    this._loading = false;
  }

  render(): TemplateResult {
    const todayStr = dayKey(new Date());

    return html`
      <div class="header">
        <h2>Timeline</h2>
        <div class="nav">
          <button @click=${() => this._navigate(this._expandedDay ? -1 : -7)}>&#9664;</button>
          <button @click=${this._goToday}>Today</button>
          <button @click=${() => this._navigate(this._expandedDay ? 1 : 7)}>&#9654;</button>
          <input type="date" .value=${toISODate(this._centerDate)} @change=${this._onDateInput} />
        </div>
      </div>

      ${this._loading
        ? html`<div class="loading">Loading...</div>`
        : this._error
          ? html`<div class="error">${this._error}</div>`
          : this._days.length === 0
            ? html`<div class="empty">No data in this window.</div>`
            : html`
                <div class="gantt">
                  ${!this._expandedDay
                    ? html`
                        <div class="hour-labels">
                          ${Array.from(
                            { length: 24 },
                            (_, i) =>
                              html`<div class="hour-label">
                                ${i === 0 ? "12a" : i < 12 ? `${i}a` : i === 12 ? "12p" : `${i - 12}p`}
                              </div>`,
                          )}
                        </div>
                      `
                    : ""}
                  ${this._days.map((day) => {
                    const isExpanded = this._expandedDay === day.dateKey;
                    if (this._expandedDay && !isExpanded) return "";
                    return html`
                      <shenas-day-row
                        .day=${day}
                        ?is-today=${day.dateKey === todayStr}
                        ?expanded=${isExpanded}
                        @day-click=${this._onDayClick}
                        @day-back=${this._onDayBack}
                      ></shenas-day-row>
                    `;
                  })}
                </div>

                ${this._renderLegend()}
              `}
    `;
  }

  _renderLegend(): TemplateResult {
    const categories = new Set<string>();
    for (const day of this._days) {
      for (const item of day.items) {
        if (item.type === "event" && (item as EventItem).category) {
          categories.add((item as EventItem).category!);
        }
      }
    }

    return html`
      <div class="legend">
        ${[...categories].map(
          (cat) => html`
            <div class="legend-item">
              <div class="legend-dot" style="background: ${categoryColor(cat)}"></div>
              ${cat}
            </div>
          `,
        )}
      </div>
    `;
  }
}

customElements.define("shenas-timeline", ShenasTimeline);
