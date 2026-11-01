import { NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Radar, Settings as SettingsIcon, SlidersHorizontal, LogOut } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/pulse", label: "Market Pulse", icon: Radar },
  { to: "/watchlist", label: "Watchlist", icon: SlidersHorizontal },
  { to: "/preferences", label: "Preferences", icon: SettingsIcon },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-ink" />
            <span className="font-display text-lg tracking-tight">Market Pulse</span>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive ? "bg-ink text-surface" : "text-muted hover:text-ink hover:bg-line/50"
                  }`
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-sm text-muted">{user?.display_name}</span>
            <button
              onClick={async () => { await logout(); navigate("/login"); }}
              className="flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        </div>

        <nav className="md:hidden flex items-center gap-1 px-4 pb-3 overflow-x-auto">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                  isActive ? "bg-ink text-surface" : "text-muted bg-line/40"
                }`
              }
            >
              <Icon className="w-3 h-3" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
