from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    onboarded: bool

    class Config:
        from_attributes = True


# ---------- Watchlists ----------

class WatchlistCreate(BaseModel):
    name: str = Field(default="My Watchlist", max_length=120)


class WatchlistUpdate(BaseModel):
    name: str = Field(max_length=120)


class WatchlistOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    class Config:
        from_attributes = True


class AddStockRequest(BaseModel):
    symbol: str = Field(max_length=32)
    price_threshold_pct: float | None = None


class InstrumentOut(BaseModel):
    symbol: str
    name: str
    exchange: str
    sector: str

    class Config:
        from_attributes = True


# ---------- Market state / change story ----------

class QuoteOut(BaseModel):
    symbol: str
    price: float
    volume: int
    avg_volume: float
    benchmark_change_pct: float
    volatility: float
    quality: str
    delayed: bool
    market_timestamp: datetime
    received_at: datetime
    freshness_seconds: float


class AttentionOut(BaseModel):
    total_score: float
    severity: str
    price_component: float
    volume_component: float
    benchmark_component: float
    volatility_component: float
    reasons: list[str]


class ChangeSummaryOut(BaseModel):
    symbol: str
    name: str
    severity: str
    attention_score: float
    previous_price: float | None
    current_price: float
    price_change_abs: float
    price_change_pct: float
    volume_ratio: float
    quality: str
    reasons: list[str]


class TimelinePoint(BaseModel):
    timestamp: datetime
    label: str


class ChangeStoryOut(BaseModel):
    symbol: str
    name: str
    attention: AttentionOut
    previous_price: float | None
    current_price: float
    price_change_abs: float
    price_change_pct: float
    volume_ratio: float
    benchmark_divergence_pct: float
    volatility_now: float
    last_checked_at: datetime | None
    current_timestamp: datetime
    quality: str
    delayed: bool
    timeline: list[TimelinePoint]


class YouWereAwayOut(BaseModel):
    last_checked_at: datetime | None
    away_seconds: float | None
    total_changed: int
    total_high_attention: int
    total_unchanged: int


class AttentionSummaryOut(BaseModel):
    you_were_away: YouWereAwayOut
    top_changes: list[ChangeSummaryOut]
    unchanged: list[ChangeSummaryOut]
    all_changes: list[ChangeSummaryOut]


class MarketStateItemOut(BaseModel):
    symbol: str
    name: str
    sector: str
    quote: QuoteOut
    attention_score: float
    severity: str


class MarketStateOut(BaseModel):
    watchlist_id: str
    generated_at: datetime
    items: list[MarketStateItemOut]


# ---------- Preferences ----------

class PreferencesOut(BaseModel):
    price_threshold_pct: float
    volume_spike_multiplier: float
    benchmark_divergence_threshold_pct: float
    notify_on_critical_only: bool
    theme: str

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    price_threshold_pct: float | None = None
    volume_spike_multiplier: float | None = None
    benchmark_divergence_threshold_pct: float | None = None
    notify_on_critical_only: bool | None = None
    theme: str | None = None
