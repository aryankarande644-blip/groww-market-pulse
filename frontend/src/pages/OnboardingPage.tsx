import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Search } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCreateWatchlist, useStockSearch } from "../hooks/useWatchlist";
import { useAuth } from "../hooks/useAuth";
import { authApi } from "../api/auth";
import { watchlistApi } from "../api/watchlists";

const SUGGESTED = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "TATAMOTORS", "ICICIBANK"];

export function OnboardingPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const createWatchlist = useCreateWatchlist();
  const [watchlistId, setWatchlistId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const { data: searchResults } = useStockSearch(query);

  async function ensureWatchlist(): Promise<string> {
    if (watchlistId) return watchlistId;
    const wl = await createWatchlist.mutateAsync("My Watchlist");
    setWatchlistId(wl.id);
    return wl.id;
  }

  async function toggle(symbol: string) {
    if (selected.includes(symbol)) return;
    // Resolve the watchlist id directly rather than through the mutation
    // hook, which may still be bound to the pre-creation (undefined) id in
    // this same render pass.
    const id = await ensureWatchlist();
    await watchlistApi.addStock(id, symbol);
    setSelected((prev) => [...prev, symbol]);
    queryClient.invalidateQueries({ queryKey: ["watchlists"] });
  }

  async function finish() {
    await ensureWatchlist();
    await authApi.completeOnboarding();
    refreshUser();
    navigate("/pulse");
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-lg">
        <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted mb-2 text-center">Step 1 of 1</p>
        <h1 className="font-display text-3xl text-center mb-2">Build your first watchlist</h1>
        <p className="text-muted text-center mb-8">Pick a few stocks to start with. You can add more any time.</p>

        <div className="border border-line bg-panel rounded-2xl p-6 mb-6">
          <div className="relative mb-4">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search any stock (e.g. Wipro, Sun Pharma)"
              className="w-full border border-line rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ink/20"
            />
          </div>

          {query && searchResults && (
            <div className="space-y-1 mb-4">
              {searchResults.map((r) => (
                <button
                  key={r.symbol}
                  onClick={() => toggle(r.symbol)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-surface text-sm text-left"
                >
                  <span>{r.name} <span className="text-muted font-mono text-xs">{r.symbol}</span></span>
                  {selected.includes(r.symbol) ? <Check className="w-4 h-4 text-rise" /> : null}
                </button>
              ))}
            </div>
          )}

          <p className="text-xs text-muted uppercase tracking-wide mb-2">Popular</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((symbol) => {
              const isSelected = selected.includes(symbol);
              return (
                <button
                  key={symbol}
                  onClick={() => toggle(symbol)}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-colors flex items-center gap-1.5 ${
                    isSelected ? "bg-ink text-surface border-ink" : "border-line hover:border-ink/40"
                  }`}
                >
                  {symbol} {isSelected && <Check className="w-3 h-3" />}
                </button>
              );
            })}
          </div>
        </div>

        <button
          onClick={finish}
          disabled={selected.length === 0}
          className="w-full bg-ink text-surface rounded-xl py-3 text-sm font-medium hover:bg-ink/90 transition-colors disabled:opacity-40"
        >
          {selected.length === 0 ? "Select at least one stock" : `Continue with ${selected.length} stock${selected.length > 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}
