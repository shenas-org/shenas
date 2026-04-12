declare module "shenas-frontends" {
  export interface RowData {
    [key: string]: unknown;
  }
  export interface Table {
    schema: { fields: Array<{ name: string }> };
    batches: unknown[];
  }
  export function query(base: string, sql: string): Promise<Table>;
  export function arrowToRows(table: Table): RowData[];
  export function arrowToColumns(table: Table): Record<string, ArrayLike<unknown>>;
  export function arrowDatesToUnix(arr: ArrayLike<unknown>): Float64Array;

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
  export interface BarPosition {
    leftPct: number;
    widthPct: number;
    end: Date | undefined;
  }
  export const CATEGORY_COLORS: Record<string, string>;
  export function categoryColor(cat: string | undefined): string;
  export function formatTime(date: Date): string;
  export function formatDate(date: Date): string;
  export function dayKey(date: Date): string;
  export function computeBarPosition(start: Date, durationMin?: number, endAt?: bigint | number): BarPosition;
}
