import type { Severity } from "../types";

export function formatINR(value: number): string {
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

export function formatPct(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatVolume(value: number): string {
  if (value >= 10_000_000) return `${(value / 10_000_000).toFixed(1)}Cr`;
  if (value >= 100_000) return `${(value / 100_000).toFixed(1)}L`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return `${value}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}

export function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function formatClockLong(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short",
  });
}

/** The attention-severity visual language: distinct from plain green/red
 * market-direction colors, on purpose (see README -> "Attention severity
 * should have its own visual language"). */
export const SEVERITY_STYLES: Record<Severity, { text: string; bg: string; ring: string; dot: string; label: string }> = {
  NORMAL:   { text: "text-gray-500",    bg: "bg-gray-100",    ring: "ring-gray-300",    dot: "bg-attention-normal",   label: "Normal" },
  LOW:      { text: "text-sky-700",     bg: "bg-sky-50",      ring: "ring-sky-300",     dot: "bg-attention-low",     label: "Low attention" },
  MODERATE: { text: "text-amber-700",   bg: "bg-amber-50",    ring: "ring-amber-300",   dot: "bg-attention-moderate",label: "Moderate attention" },
  HIGH:     { text: "text-orange-800",  bg: "bg-orange-50",   ring: "ring-orange-400",  dot: "bg-attention-high",    label: "High attention" },
  CRITICAL: { text: "text-red-800",     bg: "bg-red-50",      ring: "ring-red-400",     dot: "bg-attention-critical",label: "Critical attention" },
};

export function severityRadius(score: number): number {
  // Node radius on the Market Radar scales with attention, not raw price.
  return 22 + Math.min(26, (score / 100) * 26);
}
