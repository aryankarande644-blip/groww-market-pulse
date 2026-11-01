import { useState } from "react";
import { AppShell } from "../components/AppShell";
import { useAuth } from "../hooks/useAuth";
import { useWatchlists } from "../hooks/useWatchlist";
import { watchlistApi } from "../api/watchlists";
import { useQueryClient } from "@tanstack/react-query";

export function SettingsPage() {
  const { user, logout } = useAuth();
  const { data: watchlists } = useWatchlists();
  const queryClient = useQueryClient();
  const [renaming, setRenaming] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState("");

  async function rename(id: string) {
    await watchlistApi.rename(id, nameDraft);
    setRenaming(null);
    queryClient.invalidateQueries({ queryKey: ["watchlists"] });
  }

  return (
    <AppShell>
      <div className="max-w-xl space-y-10">
        <div>
          <h1 className="font-display text-2xl mb-6">Settings</h1>
          <div className="border border-line bg-panel rounded-xl p-6">
            <p className="text-xs text-muted uppercase tracking-wide mb-1">Account</p>
            <p className="font-medium">{user?.display_name}</p>
            <p className="text-sm text-muted">{user?.email}</p>
          </div>
        </div>

        <div>
          <h2 className="font-display text-lg mb-3">Your watchlists</h2>
          <div className="space-y-2">
            {watchlists?.map((wl) => (
              <div key={wl.id} className="flex items-center justify-between border border-line bg-panel rounded-xl px-4 py-3">
                {renaming === wl.id ? (
                  <input
                    autoFocus
                    value={nameDraft}
                    onChange={(e) => setNameDraft(e.target.value)}
                    onBlur={() => rename(wl.id)}
                    onKeyDown={(e) => e.key === "Enter" && rename(wl.id)}
                    className="border-b border-ink text-sm focus:outline-none"
                  />
                ) : (
                  <button onClick={() => { setRenaming(wl.id); setNameDraft(wl.name); }} className="text-sm text-left">
                    {wl.name} <span className="text-muted">({wl.item_count} stocks)</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-line pt-6">
          <button onClick={() => logout()} className="text-sm text-fall">
            Log out of Market Pulse
          </button>
        </div>
      </div>
    </AppShell>
  );
}
