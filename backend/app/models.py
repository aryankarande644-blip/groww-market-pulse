"""
SQLAlchemy ORM models.

Tables
------
users                -> account records
sessions             -> server-side session tokens (source of truth for auth state)
watchlists           -> a named list owned by a user
watchlist_items      -> instruments inside a watchlist (+ per-item threshold overrides)
instruments          -> tradable symbols (seeded, provider-agnostic)
market_snapshots     -> point-in-time market data captured from the provider
user_checkpoints     -> "last checked" marker per user+watchlist, the anchor for
                        "what changed since I last looked"
change_events        -> individual detected changes between checkpoint and current state
attention_scores     -> the computed, explainable score tied to a change event
user_preferences     -> per-user tunables (thresholds, etc.)
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint, Index, Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataQuality(str, enum.Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class Severity(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlists: Mapped[list["Watchlist"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Session(Base):
    """Server-side session token. This -- not localStorage -- is the source of truth for auth."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Instrument(Base):
    """A tradable symbol. Seeded and provider-agnostic -- a real market-data
    provider would still map onto this same table."""
    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), default="NSE")
    sector: Mapped[str] = mapped_column(String(64), default="")
    base_price: Mapped[float] = mapped_column(Float, nullable=False)  # seed anchor for mock provider

    __table_args__ = (Index("ix_instruments_symbol_exchange", "symbol", "exchange"),)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="My Watchlist")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    owner: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[list["WatchlistItem"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")
    checkpoints: Mapped[list["UserCheckpoint"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    watchlist_id: Mapped[str] = mapped_column(String(36), ForeignKey("watchlists.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Per-item override of the user's default attention threshold; null = use user preference
    price_threshold_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    instrument: Mapped["Instrument"] = relationship()

    __table_args__ = (UniqueConstraint("watchlist_id", "instrument_id", name="uq_watchlist_instrument"),)


class MarketSnapshot(Base):
    """A point-in-time capture of market data for an instrument, as returned by
    a MarketDataProvider. This is the append-only ledger the change engine
    diffs against; it is never mutated after being written."""
    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_volume: Mapped[float] = mapped_column(Float, nullable=False)  # trailing average, for anomaly detection
    benchmark_change_pct: Mapped[float] = mapped_column(Float, nullable=False)  # index move at capture time
    volatility: Mapped[float] = mapped_column(Float, nullable=False)  # rolling stdev proxy

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    quality: Mapped[DataQuality] = mapped_column(SAEnum(DataQuality), nullable=False, default=DataQuality.LIVE)
    market_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # when the price was true
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)  # when we stored it

    __table_args__ = (Index("ix_snapshots_instrument_time", "instrument_id", "market_timestamp"),)


class UserCheckpoint(Base):
    """The 'last checked' anchor. Every time a user opens the dashboard for a
    watchlist, we compare CURRENT state against the snapshot state that was
    current the last time a checkpoint was written for that watchlist."""
    __tablename__ = "user_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    watchlist_id: Mapped[str] = mapped_column(String(36), ForeignKey("watchlists.id", ondelete="CASCADE"), index=True)
    # JSON map of instrument_id -> snapshot_id that was "current" at checkpoint time
    snapshot_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="checkpoints")

    __table_args__ = (Index("ix_checkpoint_watchlist_time", "watchlist_id", "checked_at"),)


class ChangeEvent(Base):
    """A single detected, explainable change for one instrument between a
    checkpoint and the current snapshot."""
    __tablename__ = "change_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    watchlist_id: Mapped[str] = mapped_column(String(36), ForeignKey("watchlists.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_checkpoints.id", ondelete="CASCADE"), index=True)

    previous_snapshot_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("market_snapshots.id"), nullable=True)
    current_snapshot_id: Mapped[str] = mapped_column(String(36), ForeignKey("market_snapshots.id"))

    price_change_abs: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    volume_ratio: Mapped[float] = mapped_column(Float, default=1.0)  # current volume / avg volume
    benchmark_divergence_pct: Mapped[float] = mapped_column(Float, default=0.0)
    volatility_delta: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    attention_score: Mapped["AttentionScore"] = relationship(back_populates="change_event", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (Index("ix_change_events_watchlist_created", "watchlist_id", "created_at"),)


class AttentionScore(Base):
    """The deterministic, explainable score for a ChangeEvent. Reasons are
    stored as a JSON list of human-readable strings generated by the scoring
    engine -- never by an LLM."""
    __tablename__ = "attention_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    change_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_events.id", ondelete="CASCADE"), unique=True)

    price_component: Mapped[float] = mapped_column(Float, default=0.0)
    volume_component: Mapped[float] = mapped_column(Float, default=0.0)
    benchmark_component: Mapped[float] = mapped_column(Float, default=0.0)
    volatility_component: Mapped[float] = mapped_column(Float, default=0.0)

    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), default=Severity.NORMAL)
    reasons: Mapped[list] = mapped_column(JSON, default=list)

    change_event: Mapped["ChangeEvent"] = relationship(back_populates="attention_score")

    __table_args__ = (Index("ix_attention_severity_score", "severity", "total_score"),)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    price_threshold_pct: Mapped[float] = mapped_column(Float, default=2.0)
    volume_spike_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
    benchmark_divergence_threshold_pct: Mapped[float] = mapped_column(Float, default=1.0)
    notify_on_critical_only: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(16), default="light")

    user: Mapped["User"] = relationship(back_populates="preferences")
