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

export interface TransactionItem {
  type: "transaction";
  date?: string;
  amount?: number;
  payee?: string;
  category?: string;
  category_group?: string;
}

export interface MediaItem {
  type: "media";
  timestamp?: bigint | number;
  title?: string;
  url?: string;
  thumbnail_url?: string;
  lat?: number;
  lon?: number;
  _time?: Date;
}

export type TimelineItem = EventItem | TransactionItem | MediaItem;

export interface DailyMetrics {
  sleep_hours?: number | null;
  sleep_score?: number | null;
  rmssd?: number | null;
  resting_hr?: number | null;
  steps?: number | null;
  active_kcal?: number | null;
  mood?: number | null;
  stress?: number | null;
  productivity?: number | null;
  total_spent?: number | null;
  transaction_count?: number | null;
  weight_kg?: number | null;
}

export interface DayData {
  date: Date;
  dateKey: string;
  items: TimelineItem[];
  metrics: DailyMetrics | null;
}
