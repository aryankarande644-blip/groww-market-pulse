from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import (
    Watchlist, WatchlistItem, Instrument, User, DataQuality, Severity,
)
from app.schemas import (
    WatchlistCreate, WatchlistUpdate, WatchlistOut, AddStockRequest,
    MarketStateOut, MarketStateItemOut, QuoteOut, AttentionSummaryOut,
    YouWereAwayOut, ChangeSummaryOut,
)
from app.deps import get_current_user, get_market_data_provider
from app.market_data.provider import MarketDataProvider
from app import services

router = APIRouter(tags=["watchlists"])


def _get_owned_watchlist(db: DBSession, user: User, watchlist_id: str) -> Watchlist:
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return wl


@router.get("/watchlists", response_model=list[WatchlistOut])
def list_watchlists(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.created_at).all()
    out = []
    for wl in watchlists:
        item_count = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).count()
        out.append(WatchlistOut(id=wl.id, name=wl.name, created_at=wl.created_at, updated_at=wl.updated_at, item_count=item_count))
    return out


@router.post("/watchlists", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    wl = Watchlist(user_id=user.id, name=payload.name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return WatchlistOut(id=wl.id, name=wl.name, created_at=wl.created_at, updated_at=wl.updated_at, item_count=0)


@router.patch("/watchlists/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist(watchlist_id: str, payload: WatchlistUpdate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    wl.name = payload.name
    db.commit()
    db.refresh(wl)
    item_count = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).count()
    return WatchlistOut(id=wl.id, name=wl.name, created_at=wl.created_at, updated_at=wl.updated_at, item_count=item_count)


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    db.delete(wl)
    db.commit()
    return None


@router.post("/watchlists/{watchlist_id}/stocks", status_code=status.HTTP_201_CREATED)
def add_stock(watchlist_id: str, payload: AddStockRequest, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    symbol = payload.symbol.strip().upper()
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown symbol '{symbol}'")

    existing = db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == wl.id, WatchlistItem.instrument_id == instrument.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{symbol} is already in this watchlist")

    item = WatchlistItem(watchlist_id=wl.id, instrument_id=instrument.id, price_threshold_pct=payload.price_threshold_pct)
    db.add(item)
    db.commit()
    return {"symbol": symbol, "added": True}


@router.delete("/watchlists/{watchlist_id}/stocks/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_stock(watchlist_id: str, symbol: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol.upper()).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown symbol")
    item = db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == wl.id, WatchlistItem.instrument_id == instrument.id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol is not in this watchlist")
    db.delete(item)
    db.commit()
    return None


def _quote_out(snap, quality_seconds_threshold_stale: int, quality_seconds_threshold_delayed: int) -> QuoteOut:
    fresh = services.freshness_seconds(snap)
    return QuoteOut(
        symbol=snap.instrument.symbol if hasattr(snap, "instrument") else "",
        price=snap.price, volume=snap.volume, avg_volume=snap.avg_volume,
        benchmark_change_pct=snap.benchmark_change_pct, volatility=snap.volatility,
        quality=snap.quality.value, delayed=snap.quality in (DataQuality.DELAYED, DataQuality.STALE),
        market_timestamp=snap.market_timestamp, received_at=snap.received_at,
        freshness_seconds=fresh,
    )


@router.get("/watchlists/{watchlist_id}/market-state", response_model=MarketStateOut)
def market_state(
    watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    """Live radar view: current tick + tick-over-tick attention (NOT relative
    to the user's last visit -- see /attention-summary for that)."""
    wl = _get_owned_watchlist(db, user, watchlist_id)
    prefs = services.get_preferences(db, user.id)
    instruments = services.get_watchlist_symbols(db, wl.id)
    current_by_symbol = services.get_or_bootstrap_current_state(db, provider, wl)

    items: list[MarketStateItemOut] = []
    for instrument in instruments:
        current = current_by_symbol[instrument.symbol]
        # Compare against the snapshot immediately before this one, if any,
        # purely to drive the radar's "recent momentum" attention score.
        history = (
            db.query(services.MarketSnapshot)
            .filter(services.MarketSnapshot.instrument_id == instrument.id)
            .order_by(services.MarketSnapshot.received_at.desc())
            .limit(2)
            .all()
        )
        previous = history[1] if len(history) > 1 else None
        item = next((wi for wi in wl.items if wi.instrument_id == instrument.id), None)
        threshold_override = item.price_threshold_pct if item else None

        breakdown, _delta = services.compute_change_for_instrument(
            db, instrument=instrument, current=current, previous=previous,
            prefs=prefs, item_threshold_override=threshold_override,
        )
        quote = _quote_out(current, 0, 0)
        quote.symbol = instrument.symbol
        items.append(MarketStateItemOut(
            symbol=instrument.symbol, name=instrument.name, sector=instrument.sector,
            quote=quote, attention_score=breakdown.total_score, severity=breakdown.severity.value,
        ))

    return MarketStateOut(watchlist_id=wl.id, generated_at=datetime.now(timezone.utc), items=items)


def _compute_all_changes(db: DBSession, user: User, wl: Watchlist, provider: MarketDataProvider):
    """Shared computation for /changes and /attention-summary: diff against
    the last checkpoint (the anchor for 'since you last looked')."""
    prefs = services.get_preferences(db, user.id)
    instruments = services.get_watchlist_symbols(db, wl.id)
    current_by_symbol = services.get_or_bootstrap_current_state(db, provider, wl)
    last_checkpoint = services.get_last_checkpoint(db, wl.id)

    # Bootstrap: first-ever visit has no checkpoint yet. Create one now so
    # future visits have something to compare against; everything reads as
    # unchanged on this very first call, which is the correct behaviour.
    if not last_checkpoint:
        refs = {i.symbol: current_by_symbol[i.symbol].id for i in instruments}
        last_checkpoint = services.write_checkpoint(db, user.id, wl.id, refs)
        previous_lookup = {i.symbol: current_by_symbol[i.symbol] for i in instruments}
    else:
        previous_lookup = {}
        for i in instruments:
            snap_id = last_checkpoint.snapshot_refs.get(i.symbol)
            previous_lookup[i.symbol] = (
                db.query(services.MarketSnapshot).filter(services.MarketSnapshot.id == snap_id).first()
                if snap_id else None
            )

    summaries: list[ChangeSummaryOut] = []
    for instrument in instruments:
        current = current_by_symbol[instrument.symbol]
        previous = previous_lookup.get(instrument.symbol)
        item = next((wi for wi in wl.items if wi.instrument_id == instrument.id), None)
        threshold_override = item.price_threshold_pct if item else None

        event, score = services.get_or_create_change_event(
            db, watchlist_id=wl.id, instrument=instrument, checkpoint=last_checkpoint,
            current=current, previous=previous, prefs=prefs, item_threshold_override=threshold_override,
        )
        summaries.append(ChangeSummaryOut(
            symbol=instrument.symbol, name=instrument.name, severity=score.severity.value,
            attention_score=score.total_score,
            previous_price=previous.price if previous else None,
            current_price=current.price,
            price_change_abs=event.price_change_abs, price_change_pct=event.price_change_pct,
            volume_ratio=event.volume_ratio, quality=current.quality.value, reasons=score.reasons,
        ))

    return last_checkpoint, summaries


@router.get("/watchlists/{watchlist_id}/changes", response_model=list[ChangeSummaryOut])
def get_changes(
    watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    _, summaries = _compute_all_changes(db, user, wl, provider)
    return sorted(summaries, key=lambda s: s.attention_score, reverse=True)


@router.get("/watchlists/{watchlist_id}/attention-summary", response_model=AttentionSummaryOut)
def attention_summary(
    watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    wl = _get_owned_watchlist(db, user, watchlist_id)
    checkpoint, summaries = _compute_all_changes(db, user, wl, provider)

    NORMAL_FLOOR = 30.0  # below LOW severity => "did not meaningfully change"
    meaningfully_changed = [s for s in summaries if s.attention_score >= NORMAL_FLOOR]
    unchanged = [s for s in summaries if s.attention_score < NORMAL_FLOOR]
    high_attention = [s for s in summaries if s.severity in (Severity.HIGH.value, Severity.CRITICAL.value)]

    away_seconds = None
    if checkpoint and checkpoint.checked_at:
        now = datetime.now(timezone.utc)
        checked_at = checkpoint.checked_at if checkpoint.checked_at.tzinfo else checkpoint.checked_at.replace(tzinfo=timezone.utc)
        away_seconds = max(0.0, (now - checked_at).total_seconds())

    top_changes = sorted(meaningfully_changed, key=lambda s: s.attention_score, reverse=True)[:10]

    return AttentionSummaryOut(
        you_were_away=YouWereAwayOut(
            last_checked_at=checkpoint.checked_at if checkpoint else None,
            away_seconds=away_seconds,
            total_changed=len(meaningfully_changed),
            total_high_attention=len(high_attention),
            total_unchanged=len(unchanged),
        ),
        top_changes=top_changes,
        unchanged=unchanged,
        all_changes=sorted(summaries, key=lambda s: s.attention_score, reverse=True),
    )


@router.post("/watchlists/{watchlist_id}/checkpoint", status_code=status.HTTP_201_CREATED)
def create_checkpoint(
    watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    """Explicitly mark 'I have seen the current state' -- moves the anchor
    used by /attention-summary and /changes forward to right now."""
    wl = _get_owned_watchlist(db, user, watchlist_id)
    instruments = services.get_watchlist_symbols(db, wl.id)
    current_by_symbol = services.get_or_bootstrap_current_state(db, provider, wl)
    refs = {i.symbol: current_by_symbol[i.symbol].id for i in instruments}
    cp = services.write_checkpoint(db, user.id, wl.id, refs)
    return {"checkpoint_id": cp.id, "checked_at": cp.checked_at}


@router.post("/watchlists/{watchlist_id}/simulate", response_model=MarketStateOut)
def simulate_market_update(
    watchlist_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    """Advance the mock market by one tick for every instrument in this
    watchlist. Not part of the literal endpoint list in the brief, but
    required to make 'Simulate Market Update' in the demo actually do
    something real -- it generates genuinely new snapshots (not fake UI
    state), which then flow through the same change/attention pipeline as
    everything else."""
    wl = _get_owned_watchlist(db, user, watchlist_id)
    instruments = services.get_watchlist_symbols(db, wl.id)
    services.refresh_snapshots(db, provider, instruments)
    return market_state(watchlist_id, db, user, provider)
