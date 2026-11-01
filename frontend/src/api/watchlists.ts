import { api } from "../lib/api-client";
import type {
  Watchlist, MarketState, AttentionSummary, ChangeSummary, Instrument, ChangeStory, Preferences,
} from "../types";

export const watchlistApi = {
  list: () => api.get<Watchlist[]>("/watchlists"),
  create: (name: string) => api.post<Watchlist>("/watchlists", { name }),
  rename: (id: string, name: string) => api.patch<Watchlist>(`/watchlists/${id}`, { name }),
  remove: (id: string) => api.delete<void>(`/watchlists/${id}`),

  addStock: (watchlistId: string, symbol: string, price_threshold_pct?: number) =>
    api.post<{ symbol: string; added: boolean }>(`/watchlists/${watchlistId}/stocks`, { symbol, price_threshold_pct }),
  removeStock: (watchlistId: string, symbol: string) =>
    api.delete<void>(`/watchlists/${watchlistId}/stocks/${symbol}`),

  marketState: (watchlistId: string) => api.get<MarketState>(`/watchlists/${watchlistId}/market-state`),
  changes: (watchlistId: string) => api.get<ChangeSummary[]>(`/watchlists/${watchlistId}/changes`),
  attentionSummary: (watchlistId: string) => api.get<AttentionSummary>(`/watchlists/${watchlistId}/attention-summary`),
  checkpoint: (watchlistId: string) => api.post<{ checkpoint_id: string; checked_at: string }>(`/watchlists/${watchlistId}/checkpoint`),
  simulate: (watchlistId: string) => api.post<MarketState>(`/watchlists/${watchlistId}/simulate`),
};

export const stocksApi = {
  search: (q: string) => api.get<Instrument[]>(`/stocks/search?q=${encodeURIComponent(q)}`),
  changeStory: (symbol: string, watchlistId: string) =>
    api.get<ChangeStory>(`/stocks/${symbol}/change-story?watchlist_id=${encodeURIComponent(watchlistId)}`),
};

export const preferencesApi = {
  get: () => api.get<Preferences>("/preferences"),
  update: (patch: Partial<Preferences>) => api.patch<Preferences>("/preferences", patch),
};
