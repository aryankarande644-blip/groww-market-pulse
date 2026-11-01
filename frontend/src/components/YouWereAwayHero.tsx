import { formatDuration, formatClockLong } from "../lib/format";
import type { YouWereAway } from "../types";

export function YouWereAwayHero({ data }: { data: YouWereAway }) {
  const hasHistory = !!data.last_checked_at;

  return (
    <div className="animate-fadeUp rounded-2xl border border-line bg-panel px-8 py-10 shadow-subtle">
      <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted mb-3">You were away</p>

      {hasHistory ? (
        <>
          <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2 mb-6">
            <div>
              <p className="text-xs text-muted mb-1">Last checked</p>
              <p className="font-display text-2xl">{formatClockLong(data.last_checked_at!)}</p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">You were away</p>
              <p className="font-display text-2xl">{formatDuration(data.away_seconds ?? 0)}</p>
            </div>
          </div>

          <h1 className="font-display text-3xl md:text-4xl leading-snug">
            {data.total_changed} {data.total_changed === 1 ? "stock" : "stocks"} changed.
          </h1>
          <h2 className="font-display text-3xl md:text-4xl leading-snug text-rise">
            {data.total_high_attention} {data.total_high_attention === 1 ? "deserves" : "deserve"} your attention.
          </h2>
        </>
      ) : (
        <h1 className="font-display text-3xl md:text-4xl leading-snug">
          Welcome to your watchlist. This is your first look at the market.
        </h1>
      )}
    </div>
  );
}
