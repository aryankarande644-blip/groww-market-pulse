import { useState } from "react";
import { Search, Plus, Check } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { useWatchlists, useStockSearch, useAddStock } from "../hooks/useWatchlist";

export function StockSearchPage() {
  const [query, setQuery] = useState("");
  const { data: results, isLoading } = useStockSearch(query);
  const { data: watchlists } = useWatchlists();
  const activeWatchlistId = watchlists?.[0]?.id;
  const addStock = useAddStock(activeWatchlistId);
  const [added, setAdded] = useState<string[]>([]);

  async function handleAdd(symbol: string) {
    if (!activeWatchlistId) return;
    await addStock.mutateAsync(symbol);
    setAdded((prev) => [...prev, symbol]);
  }

  return (
    <AppShell>
      <h1 className="font-display text-2xl mb-6">Search stocks</h1>

      <div className="relative max-w-xl mb-8">
        <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by symbol or company name"
          className="w-full border border-line bg-panel rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-ink/20"
        />
      </div>

      {isLoading && <p className="text-muted text-sm">Searching…</p>}

      <div className="max-w-xl space-y-2">
        {(results ?? []).map((r) => {
          const isAdded = added.includes(r.symbol);
          return (
            <div key={r.symbol} className="flex items-center justify-between border border-line bg-panel rounded-xl px-4 py-3">
              <div>
                <p className="font-medium">{r.name}</p>
                <p className="text-xs text-muted font-mono">{r.symbol} · {r.exchange} · {r.sector}</p>
              </div>
              <button
                onClick={() => handleAdd(r.symbol)}
                disabled={isAdded || !activeWatchlistId}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  isAdded ? "text-rise" : "border border-line hover:border-ink/30"
                }`}
              >
                {isAdded ? <><Check className="w-3.5 h-3.5" /> Added</> : <><Plus className="w-3.5 h-3.5" /> Add</>}
              </button>
            </div>
          );
        })}
        {query && !isLoading && results?.length === 0 && (
          <p className="text-muted text-sm">No matches for "{query}".</p>
        )}
      </div>
    </AppShell>
  );
}
