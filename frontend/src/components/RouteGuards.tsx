import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;
  return <>{children}</>;
}

export function RequireOnboarding({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-muted">Loading…</div>;
  if (user) return <Navigate to={user.onboarded ? "/pulse" : "/onboarding"} replace />;
  return <>{children}</>;
}
