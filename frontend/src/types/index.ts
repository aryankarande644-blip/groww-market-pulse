export type DataQuality = "LIVE" | "DELAYED" | "STALE" | "UNAVAILABLE";
export type Severity = "NORMAL" | "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export interface User {
  id: string;
  email: string;
  display_name: string;
  onboarded: boolean;
}

export interface Watchlist {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  item_count: number;
}

export interface Instrument {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
}

export interface Quote {
  symbol: string;
  price: number;
  volume: number;
  avg_volume: number;
  benchmark_change_pct: number;
  volatility: number;
  quality: DataQuality;
  delayed: boolean;
  market_timestamp: string;
  received_at: string;
  freshness_seconds: number;
}

export interface MarketStateItem {
  symbol: string;
  name: string;
  sector: string;
  quote: Quote;
  attention_score: number;
  severity: Severity;
}

export interface MarketState {
  watchlist_id: string;
  generated_at: string;
  items: MarketStateItem[];
}

export interface ChangeSummary {
  symbol: string;
  name: string;
  severity: Severity;
  attention_score: number;
  previous_price: number | null;
  current_price: number;
  price_change_abs: number;
  price_change_pct: number;
  volume_ratio: number;
  quality: DataQuality;
  reasons: string[];
}

export interface YouWereAway {
  last_checked_at: string | null;
  away_seconds: number | null;
  total_changed: number;
  total_high_attention: number;
  total_unchanged: number;
}

export interface AttentionSummary {
  you_were_away: YouWereAway;
  top_changes: ChangeSummary[];
  unchanged: ChangeSummary[];
  all_changes: ChangeSummary[];
}

export interface AttentionBreakdown {
  total_score: number;
  severity: Severity;
  price_component: number;
  volume_component: number;
  benchmark_component: number;
  volatility_component: number;
  reasons: string[];
}

export interface TimelinePoint {
  timestamp: string;
  label: string;
}

export interface ChangeStory {
  symbol: string;
  name: string;
  attention: AttentionBreakdown;
  previous_price: number | null;
  current_price: number;
  price_change_abs: number;
  price_change_pct: number;
  volume_ratio: number;
  benchmark_divergence_pct: number;
  volatility_now: number;
  last_checked_at: string | null;
  current_timestamp: string;
  quality: DataQuality;
  delayed: boolean;
  timeline: TimelinePoint[];
}

export interface Preferences {
  price_threshold_pct: number;
  volume_spike_multiplier: number;
  benchmark_divergence_threshold_pct: number;
  notify_on_critical_only: boolean;
  theme: string;
}
