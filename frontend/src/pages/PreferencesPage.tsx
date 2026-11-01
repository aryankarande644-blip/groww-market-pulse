import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { usePreferences, useUpdatePreferences } from "../hooks/useWatchlist";

export function PreferencesPage() {
  const { data: prefs, isLoading } = usePreferences();
  const update = useUpdatePreferences();

  const [priceThreshold, setPriceThreshold] = useState(2);
  const [volumeMultiplier, setVolumeMultiplier] = useState(2);
  const [benchmarkThreshold, setBenchmarkThreshold] = useState(1);
  const [criticalOnly, setCriticalOnly] = useState(false);

  useEffect(() => {
    if (prefs) {
      setPriceThreshold(prefs.price_threshold_pct);
      setVolumeMultiplier(prefs.volume_spike_multiplier);
      setBenchmarkThreshold(prefs.benchmark_divergence_threshold_pct);
      setCriticalOnly(prefs.notify_on_critical_only);
    }
  }, [prefs]);

  function save() {
    update.mutate({
      price_threshold_pct: priceThreshold,
      volume_spike_multiplier: volumeMultiplier,
      benchmark_divergence_threshold_pct: benchmarkThreshold,
      notify_on_critical_only: criticalOnly,
    });
  }

  if (isLoading) return <AppShell><div className="text-muted py-24 text-center">Loading…</div></AppShell>;

  return (
    <AppShell>
      <div className="max-w-xl">
        <h1 className="font-display text-2xl mb-2">Preferences</h1>
        <p className="text-muted text-sm mb-8">
          These thresholds directly drive the meaningful-change engine — they're not cosmetic.
          Lower thresholds mean more stocks will be flagged for attention.
        </p>

        <div className="space-y-8">
          <SliderField
            label="Price move threshold"
            hint="A price move below this is not, by itself, considered meaningful."
            value={priceThreshold} min={0.5} max={10} step={0.5} unit="%"
            onChange={setPriceThreshold}
          />
          <SliderField
            label="Volume spike multiplier"
            hint="Volume must exceed this multiple of the recent average to count as anomalous."
            value={volumeMultiplier} min={1.2} max={5} step={0.1} unit="×"
            onChange={setVolumeMultiplier}
          />
          <SliderField
            label="Benchmark divergence threshold"
            hint="How far a stock must move relative to the index before it's flagged as idiosyncratic."
            value={benchmarkThreshold} min={0.2} max={5} step={0.1} unit="%"
            onChange={setBenchmarkThreshold}
          />

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox" checked={criticalOnly} onChange={(e) => setCriticalOnly(e.target.checked)}
              className="w-4 h-4 accent-ink"
            />
            <span className="text-sm">Only surface CRITICAL severity in "Top changes"</span>
          </label>

          <button
            onClick={save}
            disabled={update.isPending}
            className="bg-ink text-surface px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-ink/90 disabled:opacity-60"
          >
            {update.isPending ? "Saving…" : "Save preferences"}
          </button>
          {update.isSuccess && <p className="text-sm text-rise mt-2">Saved.</p>}
        </div>
      </div>
    </AppShell>
  );
}

function SliderField({
  label, hint, value, min, max, step, unit, onChange,
}: {
  label: string; hint: string; value: number; min: number; max: number; step: number; unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium">{label}</label>
        <span className="num text-sm text-muted">{value}{unit}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-ink"
      />
      <p className="text-xs text-muted mt-1">{hint}</p>
    </div>
  );
}
