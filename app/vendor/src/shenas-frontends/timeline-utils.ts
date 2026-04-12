/**
 * Shared timeline/event utilities for dashboard plugins.
 *
 * Consolidates duplicated helpers from event-gantt and timeline dashboards
 * into a single reusable module: category colors, date formatting, and
 * time-based bar positioning math.
 */

export interface EventItem {
  type: "event";
  source?: string;
  source_id?: string;
  start_at?: bigint | number;
  end_at?: bigint | number;
  duration_min?: number;
  title?: string;
  category?: string;
  location?: string;
  all_day?: boolean;
  _start?: Date;
  _end?: Date;
}

export const CATEGORY_COLORS: Record<string, string> = {
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
  return date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export interface BarPosition {
  leftPct: number;
  widthPct: number;
  end: Date | undefined;
}

/**
 * Compute the horizontal position and width of a time-based bar on a 24-hour
 * timeline, given a start time and either a duration or an end timestamp.
 *
 * Arrow timestamps arrive as microseconds since epoch; `endAt` is converted
 * with `new Date(Number(endAt) / 1000)`.
 */
export function computeBarPosition(
  start: Date,
  durationMin?: number,
  endAt?: bigint | number,
): BarPosition {
  const hours = start.getHours() + start.getMinutes() / 60;
  const leftPct = (hours / 24) * 100;
  let durationHours = ((durationMin as number) || 30) / 60;
  let end: Date | undefined;
  if (endAt) {
    end = new Date(Number(endAt) / 1000);
    durationHours = (end.getTime() - start.getTime()) / 3600000;
  }
  const widthPct = Math.max((durationHours / 24) * 100, 0.3);
  return { leftPct, widthPct, end };
}
