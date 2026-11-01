import { ChevronRight } from "lucide-react";
import type { ChangeSummary } from "../types";
import { formatINR, formatPct, SEVERITY_STYLES } from "../lib/format";

export function ChangeCard({ change, onClick }: { change: ChangeSummary; onClick: () => void }) {
  const style = SEVERITY_STYLES[change.severity];
  const isUp = change.price_change_pct >= 0;

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-line bg-panel px-5 py-4 hover:border-ink/30 hover:shadow-subtle transition-all group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              {style.label}
            </span>
            {change.quality !== "LIVE" && (
              <span className="text-[10px] font-mono uppercase tracking-wide text-amber-600">{change.quality}</span>
            )}
          </div>
          <p className="font-display text-lg mb-1">{change.name}</p>
          <div className="flex items-baseline gap-2 num text-sm">
            {change.previous_price !== null && (
              <>
                <span className="text-muted">{formatINR(change.previous_price)}</span>
                <span className="text-muted">→</span>
              </>
            )}
            <span className="font-semibold">{formatINR(change.current_price)}</span>
            <span className={isUp ? "text-rise" : "text-fall"}>{formatPct(change.price_change_pct)}</span>
          </div>
          {change.reasons.length > 0 && (
            <p className="text-xs text-muted mt-2 line-clamp-1">{change.reasons[0]}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <span className="font-mono text-xs text-muted">{Math.round(change.attention_score)}/100</span>
          <ChevronRight className="w-4 h-4 text-muted group-hover:text-ink group-hover:translate-x-0.5 transition-all" />
        </div>
      </div>
    </button>
  );
}
