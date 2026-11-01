import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Zap, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { YouWereAwayHero } from "../components/YouWereAwayHero";
import { MarketRadar } from "../components/MarketRadar";
import { ChangeCard } from "../components/ChangeCard";
import { ChangeStoryDrawer } from "../components/ChangeStoryDrawer";
import {
  useWatchlists, useMarketState, useAttentionSummary, useSimulateMarketUpdate, useCheckpoint, useChangeStory,
} from "../hooks/useWatchlist";
import { formatINR } from "../lib/format";

export function MarketPulsePage() {
  const { data: watchlists, isLoading: watchlistsLoading } = useWatchlists();
  const activeWatchlistId = watchlists?.[0]?.id;

  const marketState = useMarketState(activeWatchlistId);
  const attentionSummary = useAttentionSummary(activeWatchlistId);
  const simulate = useSimulateMarketUpdate(activeWatchlistId);
  const checkpoint = useCheckpoint(activeWatchlistId);

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const story = useChangeStory(selectedSymbol ?? undefined, activeWatchlistId);

  // The dashboard view IS the "checking" event: once the user has seen the
  // "You Were Away" summary, quietly mark the current state as reviewed so
  // the next visit compares against *this* moment, not further back. This
  // keeps GET /attention-summary a pure, idempotent read while still making
  // "returning" a real, persisted event -- see README > State Persistence.
  useEffect(() => {
    if (attentionSummary.data && activeWatchlistId) {
      const t = setTimeout(() => checkpoint.mutate(), 4000);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attentionSummary.dataUpdatedAt, activeWatchlistId]);

  if (watchlistsLoading) {
    return <AppShell><div className="text-center py-24 text-muted">Loading…</div></AppShell>;
  }

  if (!activeWatchlistId) {
    return (
      <AppShell>
        <div className="text-center py-24">
          <p className="font-display text-2xl mb-3">You don't have a watchlist yet.</p>
          <Link to="/watchlist" className="text-ink underline">Create one to get started</Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-10">
        {attentionSummary.data && <YouWereAwayHero data={attentionSummary.data.you_were_away} />}

        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl">Market Radar</h2>
          <button
            onClick={() => simulate.mutate()}
            disabled={simulate.isPending}
            className="flex items-center gap-2 bg-ink text-surface px-4 py-2 rounded-lg text-sm font-medium hover:bg-ink/90 transition-colors disabled:opacity-60"
          >
            {simulate.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            Simulate Market Update
          </button>
        </div>

        {marketState.data && (
          <MarketRadar
            items={marketState.data.items}
            onSelect={setSelectedSymbol}
            selectedSymbol={selectedSymbol}
          />
        )}

        {attentionSummary.data && attentionSummary.data.top_changes.length > 0 && (
          <section>
            <h2 className="font-display text-xl mb-4">Top changes</h2>
            <div className="grid md:grid-cols-2 gap-3">
              {attentionSummary.data.top_changes.map((c) => (
                <ChangeCard key={c.symbol} change={c} onClick={() => setSelectedSymbol(c.symbol)} />
              ))}
            </div>
          </section>
        )}

        {attentionSummary.data && attentionSummary.data.unchanged.length > 0 && (
          <section>
            <h2 className="font-display text-xl mb-1">
              {attentionSummary.data.unchanged.length} {attentionSummary.data.unchanged.length === 1 ? "stock" : "stocks"} did not meaningfully change
            </h2>
            <p className="text-sm text-muted mb-4">Shown for completeness — nothing here crossed your thresholds.</p>
            <div className="flex flex-wrap gap-2">
              {attentionSummary.data.unchanged.map((c) => (
                <button
                  key={c.symbol}
                  onClick={() => setSelectedSymbol(c.symbol)}
                  className="flex items-center gap-2 border border-line bg-panel rounded-full pl-3 pr-4 py-1.5 text-sm hover:border-ink/30 transition-colors"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-attention-normal" />
                  {c.symbol}
                  <span className="num text-muted">{formatINR(c.current_price)}</span>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>

      <ChangeStoryDrawer story={story.data ?? null} onClose={() => setSelectedSymbol(null)} />
    </AppShell>
  );
}
