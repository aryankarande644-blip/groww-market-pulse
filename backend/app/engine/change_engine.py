"""
The Meaningful Change Engine.

This is a deterministic, fully explainable rules engine -- NOT an LLM, and
not a predictive model. It answers one question: "given what the user last
saw and what is true now, how much attention does this deserve, and why?"

Scoring (0-100), split into four independently-explainable components:

    Price movement        0-40   magnitude of % move relative to the user's threshold
    Volume anomaly         0-25   current volume vs trailing average
    Benchmark divergence    0-20   stock move vs index move (idiosyncratic vs market-wide)
    Volatility change       0-15   change in realized volatility vs baseline

Severity bands:
    0-29   NORMAL
    30-49  LOW
    50-69  MODERATE
    70-84  HIGH
    85-100 CRITICAL

Every score is accompanied by a list of plain-language reasons generated
directly from the same numbers that produced the score -- there is no
separate "explanation" step that could drift from the math.
"""
from dataclasses import dataclass, field

from app.models import Severity, DataQuality


@dataclass
class ScoreBreakdown:
    price_component: float
    volume_component: float
    benchmark_component: float
    volatility_component: float
    total_score: float
    severity: Severity
    reasons: list[str] = field(default_factory=list)


def _severity_for(score: float) -> Severity:
    if score >= 85:
        return Severity.CRITICAL
    if score >= 70:
        return Severity.HIGH
    if score >= 50:
        return Severity.MODERATE
    if score >= 30:
        return Severity.LOW
    return Severity.NORMAL


def score_change(
    *,
    price_change_pct: float,
    price_threshold_pct: float,
    volume_ratio: float,
    volume_spike_multiplier: float,
    benchmark_divergence_pct: float,
    benchmark_threshold_pct: float,
    volatility_now: float,
    volatility_baseline: float,
    data_quality: DataQuality,
) -> ScoreBreakdown:
    reasons: list[str] = []
    abs_pct = abs(price_change_pct)

    # --- Price movement: 0-40 ------------------------------------------------
    # Scales linearly once the move exceeds the user's threshold, saturating
    # at 2x the threshold (e.g. a 4% move against a 2% threshold maxes this
    # component out at 40).
    if price_threshold_pct <= 0:
        price_threshold_pct = 0.5
    price_ratio = abs_pct / price_threshold_pct
    price_component = min(40.0, max(0.0, price_ratio - 1.0) * 40.0) if price_ratio > 1 else 0.0
    # small baseline credit for any non-trivial move even under threshold
    if price_component == 0.0 and abs_pct > 0:
        price_component = min(8.0, (abs_pct / price_threshold_pct) * 8.0)
    if price_ratio > 1:
        direction = "up" if price_change_pct > 0 else "down"
        reasons.append(
            f"Price moved {abs_pct:.2f}% {direction}, exceeding your {price_threshold_pct:.1f}% threshold"
        )

    # --- Volume anomaly: 0-25 -------------------------------------------------
    volume_component = 0.0
    if volume_spike_multiplier <= 0:
        volume_spike_multiplier = 2.0
    if volume_ratio > 1.0:
        excess = (volume_ratio - 1.0) / (volume_spike_multiplier - 1.0) if volume_spike_multiplier > 1 else 0
        volume_component = min(25.0, max(0.0, excess) * 25.0)
        if volume_ratio >= volume_spike_multiplier:
            reasons.append(f"Volume is {volume_ratio:.1f}x recent average")

    # --- Benchmark divergence: 0-20 -------------------------------------------
    # Saturates at 2x the divergence threshold, same shape as price above.
    if benchmark_threshold_pct <= 0:
        benchmark_threshold_pct = 0.5
    div_ratio = abs(benchmark_divergence_pct) / benchmark_threshold_pct
    benchmark_component = min(20.0, max(0.0, div_ratio - 1.0) * 20.0) if div_ratio > 1 else 0.0
    if div_ratio > 1:
        verb = "outperformed" if benchmark_divergence_pct > 0 else "underperformed"
        reasons.append(f"Stock {verb} the benchmark by {abs(benchmark_divergence_pct):.2f}%")

    # --- Volatility change: 0-15 ----------------------------------------------
    volatility_component = 0.0
    if volatility_baseline > 0:
        vol_ratio = volatility_now / volatility_baseline
        if vol_ratio > 1.0:
            volatility_component = min(15.0, max(0.0, vol_ratio - 1.0) * 15.0)
            if vol_ratio >= 1.5:
                reasons.append(f"Volatility rose {vol_ratio:.1f}x versus its recent baseline")

    total = round(price_component + volume_component + benchmark_component + volatility_component, 1)
    total = min(100.0, total)
    severity = _severity_for(total)

    # Data-quality caveats are always surfaced, regardless of score.
    if data_quality == DataQuality.STALE:
        reasons.append("Data is stale -- treat this change with caution until fresh data arrives")
    elif data_quality == DataQuality.DELAYED:
        reasons.append("Data is delayed -- current values may lag the real market briefly")
    elif data_quality == DataQuality.UNAVAILABLE:
        reasons.append("Live data is currently unavailable for this instrument")

    if not reasons:
        reasons.append("No component of price, volume, benchmark, or volatility crossed your thresholds")

    return ScoreBreakdown(
        price_component=round(price_component, 1),
        volume_component=round(volume_component, 1),
        benchmark_component=round(benchmark_component, 1),
        volatility_component=round(volatility_component, 1),
        total_score=total,
        severity=severity,
        reasons=reasons,
    )
