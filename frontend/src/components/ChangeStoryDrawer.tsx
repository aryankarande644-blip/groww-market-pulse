import { X, TrendingUp, TrendingDown, Volume2, Target, Activity } from "lucide-react";
import type { ReactNode } from "react";
import type { ChangeStory } from "../types";
import { formatINR, formatPct, formatClockLong, formatClock, SEVERITY_STYLES } from "../lib/format";

export function ChangeStoryDrawer({ story, onClose }: { story: ChangeStory | null; onClose: () => void }) {
  if (!story) return null;
  const style = SEVERITY_STYLES[story.attention.severity];
  const isUp = story.price_change_pct >= 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative w-full max-w-lg h-full bg-panel shadow-2xl overflow-y-auto animate-fadeUp">
        <div className="sticky top-0 bg-panel border-b border-line px-6 py-5 flex items-start justify-between z-10">
          <div>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              {style.label}
            </span>
            <h2 className="font-display text-2xl mt-2">{story.name}</h2>
            <p className="text-xs text-muted font-mono">{story.symbol}</p>
          </div>
          <button onClick={onClose} className="p-2 -mr-2 rounded-full hover:bg-surface transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-6 space-y-8">
          {/* Attention score */}
          <div className="text-center py-6 border border-line rounded-2xl bg-surface/50">
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-muted mb-2">Attention score</p>
            <p className="font-display text-6xl">
              {Math.round(story.attention.total_score)}
              <span className="text-2xl text-muted">/100</span>
            </p>
          </div>

          {/* Before / after */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted mb-1">You last checked</p>
              <p className="num text-xl">{story.previous_price !== null ? formatINR(story.previous_price) : "—"}</p>
              {story.last_checked_at && <p className="text-xs text-muted mt-1">{formatClockLong(story.last_checked_at)}</p>}
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Current</p>
              <p className="num text-xl font-semibold">{formatINR(story.current_price)}</p>
              <p className="text-xs text-muted mt-1">{formatClockLong(story.current_timestamp)}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-line px-4 py-3">
            {isUp ? <TrendingUp className="w-5 h-5 text-rise" /> : <TrendingDown className="w-5 h-5 text-fall" />}
            <div>
              <p className={`num text-lg font-semibold ${isUp ? "text-rise" : "text-fall"}`}>{formatPct(story.price_change_pct)}</p>
              <p className="text-xs text-muted">{isUp ? "+" : ""}{story.price_change_abs.toFixed(2)} absolute change</p>
            </div>
          </div>

          {story.delayed && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Data quality: <span className="font-semibold">{story.quality}</span>. Treat this change with appropriate caution until fresher data arrives.
            </div>
          )}

          {/* Why we flagged it */}
          <div>
            <h3 className="font-display text-lg mb-3">Why we flagged it</h3>
            <ul className="space-y-2">
              {story.attention.reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-ink shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          {/* Component breakdown */}
          <div>
            <h3 className="font-display text-lg mb-3">Score breakdown</h3>
            <div className="space-y-3">
              <ScoreBar icon={<TrendingUp className="w-3.5 h-3.5" />} label="Price movement" value={story.attention.price_component} max={40} />
              <ScoreBar icon={<Volume2 className="w-3.5 h-3.5" />} label="Volume anomaly" value={story.attention.volume_component} max={25} />
              <ScoreBar icon={<Target className="w-3.5 h-3.5" />} label="Benchmark divergence" value={story.attention.benchmark_component} max={20} />
              <ScoreBar icon={<Activity className="w-3.5 h-3.5" />} label="Volatility change" value={story.attention.volatility_component} max={15} />
            </div>
          </div>

          {/* Timeline */}
          <div>
            <h3 className="font-display text-lg mb-3">Timeline</h3>
            <ol className="relative border-l border-line ml-1.5 space-y-5">
              {story.timeline.map((point, i) => (
                <li key={i} className="pl-5 relative">
                  <span className="absolute -left-[4.5px] top-1 w-2 h-2 rounded-full bg-ink" />
                  <p className="text-xs font-mono text-muted">{formatClock(point.timestamp)}</p>
                  <p className="text-sm">{point.label}</p>
                </li>
              ))}
            </ol>
          </div>

          <p className="text-xs text-muted border-t border-line pt-4">
            Market Pulse is an information and monitoring tool. It explains what changed and why it crossed
            your thresholds — it does not predict future price movement or provide investment advice.
          </p>
        </div>
      </div>
    </div>
  );
}

function ScoreBar({ icon, label, value, max }: { icon: ReactNode; label: string; value: number; max: number }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="flex items-center gap-1.5 text-muted">{icon}{label}</span>
        <span className="num text-muted">{value.toFixed(1)} / {max}</span>
      </div>
      <div className="h-1.5 rounded-full bg-line overflow-hidden">
        <div className="h-full bg-ink rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
