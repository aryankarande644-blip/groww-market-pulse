"""
Market service: the glue between the MarketDataProvider, the database, and
the change/attention engine.

Core flow implemented here (mirrors the pipeline in the brief):

    PREVIOUS STATE (last checkpoint's snapshots)
          -> CURRENT STATE (freshest snapshot per instrument)
          -> CHANGE DETECTION (numeric deltas)
          -> ATTENTION SCORE (engine.change_engine)
          -> EXPLANATION (reasons list, generated with the score)
          -> USER ATTENTION (API response)
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession, joinedload

from app.models import (
    Instrument, WatchlistItem, MarketSnapshot, UserCheckpoint,
    ChangeEvent, AttentionScore, UserPreference, DataQuality, Watchlist,
)
from app.market_data.provider import MarketDataProvider, MarketTick
from app.engine.change_engine import score_change


def _quality_flags(tick_quality: DataQuality) -> dict:
    return {
        "quality": tick_quality.value,
        "delayed": tick_quality in (DataQuality.DELAYED, DataQuality.STALE),
    }


def get_watchlist_symbols(db: DBSession, watchlist_id: str) -> list[Instrument]:
    items = (
        db.query(WatchlistItem)
        .options(joinedload(WatchlistItem.instrument))
        .filter(WatchlistItem.watchlist_id == watchlist_id)
        .all()
    )
    return [i.instrument for i in items]


def _snapshot_count(db: DBSession, instrument_id: str) -> int:
    return db.query(func.count(MarketSnapshot.id)).filter(
        MarketSnapshot.instrument_id == instrument_id
    ).scalar() or 0


def refresh_snapshots(
    db: DBSession, provider: MarketDataProvider, instruments: list[Instrument]
) -> dict[str, MarketSnapshot]:
    """Pull the latest tick per instrument from the provider and persist it as
    a new, append-only MarketSnapshot row. Returns symbol -> new snapshot."""
    if not instruments:
        return {}

    steps = {i.symbol: _snapshot_count(db, i.id) for i in instruments}
    ticks: dict[str, MarketTick] = provider.get_quotes([i.symbol for i in instruments], steps=steps)

    by_symbol = {i.symbol: i for i in instruments}
    out: dict[str, MarketSnapshot] = {}
    for symbol, tick in ticks.items():
        instrument = by_symbol[symbol]
        snap = MarketSnapshot(
            instrument_id=instrument.id,
            price=tick.price,
            volume=tick.volume,
            avg_volume=tick.avg_volume,
            benchmark_change_pct=tick.benchmark_change_pct,
            volatility=tick.volatility,
            source=tick.source,
            quality=tick.quality,
            market_timestamp=tick.market_timestamp,
            received_at=tick.received_at,
        )
        db.add(snap)
        out[symbol] = snap
    db.commit()
    for snap in out.values():
        db.refresh(snap)
    return out


def latest_snapshot(db: DBSession, instrument_id: str) -> MarketSnapshot | None:
    return (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.instrument_id == instrument_id)
        .order_by(MarketSnapshot.received_at.desc())
        .first()
    )


def get_or_bootstrap_current_state(
    db: DBSession, provider: MarketDataProvider, watchlist: Watchlist
) -> dict[str, MarketSnapshot]:
    """Ensure every instrument in the watchlist has at least one snapshot, and
    return the latest snapshot for each. Cheap and idempotent: only fetches
    for instruments missing a snapshot."""
    instruments = get_watchlist_symbols(db, watchlist.id)
    missing = [i for i in instruments if latest_snapshot(db, i.id) is None]
    if missing:
        refresh_snapshots(db, provider, missing)
    return {i.symbol: latest_snapshot(db, i.id) for i in instruments}


def get_last_checkpoint(db: DBSession, watchlist_id: str) -> UserCheckpoint | None:
    return (
        db.query(UserCheckpoint)
        .filter(UserCheckpoint.watchlist_id == watchlist_id)
        .order_by(UserCheckpoint.checked_at.desc())
        .first()
    )


def write_checkpoint(db: DBSession, user_id: str, watchlist_id: str, snapshot_refs: dict[str, str]) -> UserCheckpoint:
    cp = UserCheckpoint(user_id=user_id, watchlist_id=watchlist_id, snapshot_refs=snapshot_refs)
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp


def get_preferences(db: DBSession, user_id: str) -> UserPreference:
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def compute_change_for_instrument(
    db: DBSession,
    *,
    instrument: Instrument | None,
    current: MarketSnapshot,
    previous: MarketSnapshot | None,
    prefs: UserPreference,
    item_threshold_override: float | None,
):
    """Pure computation (no writes) of the delta + score between previous and
    current snapshot for one instrument."""
    price_threshold = item_threshold_override or prefs.price_threshold_pct
    prev_price = previous.price if previous else None

    price_change_abs = round(current.price - prev_price, 2) if prev_price is not None else 0.0
    price_change_pct = round((price_change_abs / prev_price) * 100, 3) if prev_price else 0.0
    volume_ratio = round(current.volume / current.avg_volume, 3) if current.avg_volume else 1.0
    baseline_volatility = previous.volatility if previous else current.volatility

    breakdown = score_change(
        price_change_pct=price_change_pct,
        price_threshold_pct=price_threshold,
        volume_ratio=volume_ratio,
        volume_spike_multiplier=prefs.volume_spike_multiplier,
        benchmark_divergence_pct=round(price_change_pct - current.benchmark_change_pct, 3),
        benchmark_threshold_pct=prefs.benchmark_divergence_threshold_pct,
        volatility_now=current.volatility,
        volatility_baseline=baseline_volatility,
        data_quality=current.quality,
    )
    return breakdown, {
        "prev_price": prev_price,
        "price_change_abs": price_change_abs,
        "price_change_pct": price_change_pct,
        "volume_ratio": volume_ratio,
        "benchmark_divergence_pct": round(price_change_pct - current.benchmark_change_pct, 3),
    }


def persist_change_event(
    db: DBSession,
    *,
    watchlist_id: str,
    instrument_id: str,
    checkpoint_id: str,
    previous: MarketSnapshot | None,
    current: MarketSnapshot,
    delta: dict,
    breakdown,
) -> ChangeEvent:
    event = ChangeEvent(
        watchlist_id=watchlist_id,
        instrument_id=instrument_id,
        checkpoint_id=checkpoint_id,
        previous_snapshot_id=previous.id if previous else None,
        current_snapshot_id=current.id,
        price_change_abs=delta["price_change_abs"],
        price_change_pct=delta["price_change_pct"],
        volume_ratio=delta["volume_ratio"],
        benchmark_divergence_pct=delta["benchmark_divergence_pct"],
        volatility_delta=round(current.volatility - (previous.volatility if previous else current.volatility), 3),
    )
    db.add(event)
    db.flush()  # get event.id without a full commit

    score_row = AttentionScore(
        change_event_id=event.id,
        price_component=breakdown.price_component,
        volume_component=breakdown.volume_component,
        benchmark_component=breakdown.benchmark_component,
        volatility_component=breakdown.volatility_component,
        total_score=breakdown.total_score,
        severity=breakdown.severity,
        reasons=breakdown.reasons,
    )
    db.add(score_row)
    db.commit()
    db.refresh(event)
    return event


def get_or_create_change_event(
    db: DBSession,
    *,
    watchlist_id: str,
    instrument: Instrument,
    checkpoint: UserCheckpoint,
    current: MarketSnapshot,
    previous: MarketSnapshot | None,
    prefs: UserPreference,
    item_threshold_override: float | None,
) -> tuple[ChangeEvent, "object"]:
    """Idempotent: re-fetching the same checkpoint/current pair returns the
    same persisted ChangeEvent instead of duplicating rows on every GET."""
    existing = (
        db.query(ChangeEvent)
        .filter(
            ChangeEvent.watchlist_id == watchlist_id,
            ChangeEvent.instrument_id == instrument.id,
            ChangeEvent.checkpoint_id == checkpoint.id,
            ChangeEvent.current_snapshot_id == current.id,
        )
        .first()
    )
    if existing:
        return existing, existing.attention_score

    breakdown, delta = compute_change_for_instrument(
        db, instrument=instrument, current=current, previous=previous,
        prefs=prefs, item_threshold_override=item_threshold_override,
    )
    event = persist_change_event(
        db, watchlist_id=watchlist_id, instrument_id=instrument.id,
        checkpoint_id=checkpoint.id, previous=previous, current=current,
        delta=delta, breakdown=breakdown,
    )
    return event, event.attention_score


def build_timeline(
    db: DBSession, *, instrument_id: str, checkpoint: UserCheckpoint, current: MarketSnapshot, prefs: UserPreference,
    item_threshold_override: float | None,
) -> list[dict]:
    """Reconstruct a human-readable timeline between the checkpoint and now by
    walking every intermediate snapshot and describing what first became
    true at each step."""
    timeline: list[dict] = [{"timestamp": checkpoint.checked_at, "label": "You checked"}]

    history = (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.instrument_id == instrument_id, MarketSnapshot.received_at >= checkpoint.checked_at)
        .order_by(MarketSnapshot.received_at.asc())
        .all()
    )

    prev = None
    crossed_threshold = False
    volume_flagged = False
    attention_raised = False
    for snap in history:
        if prev is not None:
            breakdown, _ = compute_change_for_instrument(
                db, instrument=None, current=snap, previous=prev,
                prefs=prefs, item_threshold_override=item_threshold_override,
            )
            if breakdown.price_component > 0 and not crossed_threshold:
                timeline.append({"timestamp": snap.received_at, "label": "Price crossed your threshold"})
                crossed_threshold = True
            if breakdown.volume_component > 15 and not volume_flagged:
                timeline.append({"timestamp": snap.received_at, "label": "Volume acceleration detected"})
                volume_flagged = True
            if breakdown.total_score >= 70 and not attention_raised:
                timeline.append({"timestamp": snap.received_at, "label": "Attention increased"})
                attention_raised = True
        prev = snap

    timeline.append({"timestamp": current.received_at, "label": "You returned"})
    return timeline


def freshness_seconds(snapshot: MarketSnapshot) -> float:
    now = datetime.now(timezone.utc)
    ts = snapshot.market_timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ts).total_seconds())
