import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/api-client";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login(email, password);
      navigate(user.onboarded ? "/pulse" : "/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function fillDemo() {
    setEmail("demo@growwpulse.app");
    setPassword("Demo@12345");
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center gap-2 justify-center mb-10">
          <div className="w-2 h-2 rounded-full bg-ink" />
          <span className="font-display text-lg">Market Pulse</span>
        </Link>

        <div className="border border-line bg-panel rounded-2xl p-8 shadow-subtle">
          <h1 className="font-display text-2xl mb-1">Welcome back</h1>
          <p className="text-sm text-muted mb-6">Log in to see what changed.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-muted mb-1 block">Email</label>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-line rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ink/20"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="text-xs text-muted mb-1 block">Password</label>
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-line rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ink/20"
                placeholder="••••••••"
              />
            </div>

            {error && <p className="text-sm text-fall">{error}</p>}

            <button
              type="submit" disabled={loading}
              className="w-full bg-ink text-surface rounded-lg py-2.5 text-sm font-medium hover:bg-ink/90 transition-colors disabled:opacity-60"
            >
              {loading ? "Logging in…" : "Log in"}
            </button>
          </form>

          <button
            onClick={fillDemo}
            type="button"
            className="w-full mt-3 border border-line rounded-lg py-2.5 text-sm text-muted hover:text-ink hover:border-ink/30 transition-colors"
          >
            Use demo account
          </button>
        </div>

        <p className="text-center text-sm text-muted mt-6">
          Don't have an account? <Link to="/register" className="text-ink underline">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
