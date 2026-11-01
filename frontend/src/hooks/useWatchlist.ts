import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { watchlistApi, stocksApi, preferencesApi } from "../api/watchlists";

export function useWatchlists() {
  return useQuery({ queryKey: ["watchlists"], queryFn: watchlistApi.list });
}

export function useCreateWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => watchlistApi.create(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useMarketState(watchlistId: string | undefined) {
  return useQuery({
    queryKey: ["market-state", watchlistId],
    queryFn: () => watchlistApi.marketState(watchlistId as string),
    enabled: !!watchlistId,
    refetchOnWindowFocus: false,
  });
}

export function useAttentionSummary(watchlistId: string | undefined) {
  return useQuery({
    queryKey: ["attention-summary", watchlistId],
    queryFn: () => watchlistApi.attentionSummary(watchlistId as string),
    enabled: !!watchlistId,
    refetchOnWindowFocus: false,
  });
}

export function useCheckpoint(watchlistId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => watchlistApi.checkpoint(watchlistId as string),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attention-summary", watchlistId] });
    },
  });
}

export function useSimulateMarketUpdate(watchlistId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => watchlistApi.simulate(watchlistId as string),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["market-state", watchlistId] });
      qc.invalidateQueries({ queryKey: ["attention-summary", watchlistId] });
    },
  });
}

export function useAddStock(watchlistId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => watchlistApi.addStock(watchlistId as string, symbol),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["market-state", watchlistId] });
      qc.invalidateQueries({ queryKey: ["attention-summary", watchlistId] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });
}

export function useRemoveStock(watchlistId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => watchlistApi.removeStock(watchlistId as string, symbol),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["market-state", watchlistId] });
      qc.invalidateQueries({ queryKey: ["attention-summary", watchlistId] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });
}

export function useStockSearch(q: string) {
  return useQuery({
    queryKey: ["stock-search", q],
    queryFn: () => stocksApi.search(q),
    enabled: q.length > 0,
  });
}

export function useChangeStory(symbol: string | undefined, watchlistId: string | undefined) {
  return useQuery({
    queryKey: ["change-story", symbol, watchlistId],
    queryFn: () => stocksApi.changeStory(symbol as string, watchlistId as string),
    enabled: !!symbol && !!watchlistId,
  });
}

export function usePreferences() {
  return useQuery({ queryKey: ["preferences"], queryFn: preferencesApi.get });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<import("../types").Preferences>) => preferencesApi.update(patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["preferences"] }),
  });
}
