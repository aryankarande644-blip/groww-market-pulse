import { useState } from "react";
import { Plus, Trash2, Search } from "lucide-react";
import { AppShell } from "../components/AppShell";
import {
  useWatchlists, useCreateWatchlist, useMarketState, useAddStock, useRemoveStock, useStockSearch,
} from "../hooks/useWatchlist";
import { formatINR } from "../lib/format";

export function WatchlistManagementPage() {
  const { data: watchlists } = useWatchlists();
  const createWatchlist = useCreateWatchlist();
  const activeWatchlistId = watchlists?.[0]?.id;

  const marketState = useMarketState(activeWatchlistId);
  const addStock = useAddStock(activeWatchlistId);
  const removeStock = useRemoveStock(activeWatchlistId);

  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState("");
  const { data: results } = useStockSearch(query);

  async function handleAdd(symbol: string) {
    try {
      await addStock.mutateAsync(symbol);
      setQuery("");
      setShowSearch(false);
    } catch {
      // Already-in-watchlist / unknown-symbol errors surface via addStock.error below.
    }
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display text-2xl">Watchlist</h1>
        {!activeWatchlistId && (
          <button
            onClick={() => createWatchlist.mutate("My Watchlist")}
            className="flex items-center gap-2 bg-ink text-surface px-4 py-2 rounded-lg text-sm font-medium hover:bg-ink/90"
          >
            <Plus className="w-4 h-4" /> Create watchlist
          </button>
        )}
      </div>

      {activeWatchlistId && (
        <>
          <div className="relative mb-6">
            <button
              onClick={() => setShowSearch((s) => !s)}
              className="flex items-center gap-2 border border-line bg-panel px-4 py-2.5 rounded-lg text-sm hover:border-ink/30 transition-colors w-full md:w-80"
            >
              <Search className="w-4 h-4 text-muted" />
              <span className="text-muted">Add a stock…</span>
            </button>

            {showSearch && (
              <div className="absolute z-20 mt-2 w-full md:w-80 border border-line bg-panel rounded-xl shadow-subtle overflow-hidden">
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search symbol or name"
                  className="w-full px-4 py-3 text-sm border-b border-line focus:outline-none"
                />
                <div className="max-h-72 overflow-y-auto">
                  {results?.map((r) => (
                    <button
                      key={r.symbol}
                      onClick={() => handleAdd(r.symbol)}
                      className="w-full text-left px-4 py-2.5 hover:bg-surface text-sm flex items-center justify-between"
                    >
                      <span>{r.name}</span>
                      <span className="font-mono text-xs text-muted">{r.symbol}</span>
                    </button>
                  ))}
                  {query && results?.length === 0 && (
                    <p className="px-4 py-3 text-sm text-muted">No matches.</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {addStock.error && (
            <p className="text-sm text-fall mb-4">{(addStock.error as Error).message}</p>
          )}

          <div className="border border-line rounded-xl bg-panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted uppercase tracking-wide">
                  <th className="px-5 py-3 font-medium">Symbol</th>
                  <th className="px-5 py-3 font-medium">Sector</th>
                  <th className="px-5 py-3 font-medium text-right">Price</th>
                  <th className="px-5 py-3 font-medium text-right">Attention</th>
                  <th className="px-5 py-3 font-medium text-right">Quality</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {marketState.data?.items.map((item) => (
                  <tr key={item.symbol} className="border-b border-line last:border-0">
                    <td className="px-5 py-3">
                      <p className="font-medium">{item.symbol}</p>
                      <p className="text-xs text-muted">{item.name}</p>
                    </td>
                    <td className="px-5 py-3 text-muted">{item.sector}</td>
                    <td className="px-5 py-3 text-right num">{formatINR(item.quote.price)}</td>
                    <td className="px-5 py-3 text-right num">{Math.round(item.attention_score)}/100</td>
                    <td className="px-5 py-3 text-right">
                      <span className={`text-xs font-mono ${item.quote.quality !== "LIVE" ? "text-amber-600" : "text-muted"}`}>
                        {item.quote.quality}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => removeStock.mutate(item.symbol)}
                        className="text-muted hover:text-fall transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {marketState.data?.items.length === 0 && (
              <p className="text-center text-muted py-10 text-sm">No stocks yet. Add your first one above.</p>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
