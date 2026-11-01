import { Link } from "react-router-dom";
import { ArrowRight, Radar } from "lucide-react";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface">
      <header className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-ink" />
          <span className="font-display text-lg tracking-tight">Market Pulse</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm text-muted hover:text-ink transition-colors">Log in</Link>
          <Link to="/register" className="text-sm bg-ink text-surface px-4 py-2 rounded-lg hover:bg-ink/90 transition-colors">
            Get started
          </Link>
        </div>
      </header>

      <section className="max-w-4xl mx-auto px-6 pt-20 pb-24 text-center">
        <p className="text-xs font-mono uppercase tracking-[0.25em] text-muted mb-6">A different kind of watchlist</p>
        <h1 className="font-display text-4xl md:text-6xl leading-tight mb-6">
          Every watchlist can tell you<br />
          <span className="text-muted">the price now.</span>
        </h1>
        <h2 className="font-display text-4xl md:text-6xl leading-tight mb-8">
          Market Pulse tells you<br />
          <span className="italic">what changed since you looked.</span>
        </h2>
        <p className="text-muted max-w-xl mx-auto mb-10">
          Deterministic, explainable attention scoring — no noise, no hype, no predictions.
          Just a clear answer to "does this deserve my attention right now?"
        </p>
        <Link
          to="/register"
          className="inline-flex items-center gap-2 bg-ink text-surface px-6 py-3 rounded-xl hover:bg-ink/90 transition-colors font-medium"
        >
          Create your first watchlist <ArrowRight className="w-4 h-4" />
        </Link>
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="border border-line rounded-2xl bg-panel p-10 flex flex-col items-center text-center gap-4">
          <Radar className="w-10 h-10 text-muted" />
          <p className="font-display text-2xl">The Market Radar</p>
          <p className="text-muted max-w-md">
            Your stocks live as nodes in an attention field. Quiet stocks stay quiet.
            The ones that need you pull toward the center and pulse.
          </p>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-24 grid md:grid-cols-3 gap-6">
        {[
          { title: "Meaningful, not noisy", body: "A deterministic scoring engine — price, volume, benchmark divergence, volatility — decides what's worth your time." },
          { title: "Always explainable", body: "Every score comes with plain-language reasons. Never a black box, never a prediction." },
          { title: "Never silently stale", body: "Live, delayed, stale, or unavailable data is always labelled — never presented as something it isn't." },
        ].map((f) => (
          <div key={f.title} className="border border-line rounded-xl bg-panel p-6">
            <p className="font-display text-lg mb-2">{f.title}</p>
            <p className="text-sm text-muted">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="max-w-6xl mx-auto px-6 py-8 border-t border-line text-xs text-muted">
        Market Pulse is an information and monitoring tool, not investment advice.
      </footer>
    </div>
  );
}
