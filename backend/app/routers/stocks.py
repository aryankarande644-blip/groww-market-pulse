from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Instrument, Watchlist, WatchlistItem, User
from app.schemas import InstrumentOut, ChangeStoryOut, AttentionOut, TimelinePoint
from app.deps import get_current_user, get_market_data_provider
from app.market_data.provider import MarketDataProvider
from app import services

router = APIRouter(tags=["stocks"])


@router.get("/stocks/search", response_model=list[InstrumentOut])
def search_stocks(q: str = Query(default="", max_length=64), db: DBSession = Depends(get_db)):
    query = db.query(Instrument)
    if q:
        like = f"%{q.upper()}%"
        query = query.filter((Instrument.symbol.ilike(like)) | (Instrument.name.ilike(like)))
    return query.order_by(Instrument.symbol).limit(25).all()


@router.get("/stocks/{symbol}/change-story", response_model=ChangeStoryOut)
def change_story(
    symbol: str,
    watchlist_id: str = Query(..., description="Which watchlist's checkpoint to compare against"),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")

    instrument = db.query(Instrument).filter(Instrument.symbol == symbol.upper()).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown symbol")

    item = db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == wl.id, WatchlistItem.instrument_id == instrument.id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol is not in this watchlist")

    prefs = services.get_preferences(db, user.id)
    current_by_symbol = services.get_or_bootstrap_current_state(db, provider, wl)
    current = current_by_symbol[instrument.symbol]

    checkpoint = services.get_last_checkpoint(db, wl.id)
    if not checkpoint:
        refs = {instrument.symbol: current.id}
        checkpoint = services.write_checkpoint(db, user.id, wl.id, refs)
        previous = current
    else:
        snap_id = checkpoint.snapshot_refs.get(instrument.symbol)
        previous = db.query(services.MarketSnapshot).filter(services.MarketSnapshot.id == snap_id).first() if snap_id else None

    event, score = services.get_or_create_change_event(
        db, watchlist_id=wl.id, instrument=instrument, checkpoint=checkpoint,
        current=current, previous=previous, prefs=prefs, item_threshold_override=item.price_threshold_pct,
    )

    timeline_raw = services.build_timeline(
        db, instrument_id=instrument.id, checkpoint=checkpoint, current=current,
        prefs=prefs, item_threshold_override=item.price_threshold_pct,
    )

    return ChangeStoryOut(
        symbol=instrument.symbol,
        name=instrument.name,
        attention=AttentionOut(
            total_score=score.total_score, severity=score.severity.value,
            price_component=score.price_component, volume_component=score.volume_component,
            benchmark_component=score.benchmark_component, volatility_component=score.volatility_component,
            reasons=score.reasons,
        ),
        previous_price=previous.price if previous else None,
        current_price=current.price,
        price_change_abs=event.price_change_abs,
        price_change_pct=event.price_change_pct,
        volume_ratio=event.volume_ratio,
        benchmark_divergence_pct=event.benchmark_divergence_pct,
        volatility_now=current.volatility,
        last_checked_at=checkpoint.checked_at,
        current_timestamp=current.market_timestamp,
        quality=current.quality.value,
        delayed=current.quality.value in ("DELAYED", "STALE"),
        timeline=[TimelinePoint(timestamp=p["timestamp"], label=p["label"]) for p in timeline_raw],
    )
