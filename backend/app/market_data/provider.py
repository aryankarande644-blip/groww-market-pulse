"""
MarketDataProvider abstraction.

The rest of the application (routers, change engine, seeding) only ever talks
to this interface. Swapping MockMarketDataProvider for a real vendor (NSE
feed, a paid API, a broker's WebSocket, ...) later means writing one new class
and changing one line of dependency wiring -- nothing else in the codebase
needs to know or care.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models import DataQuality


@dataclass
class MarketTick:
    """A single point-in-time market observation for one instrument.

    This is the ONLY shape the rest of the app depends on. It intentionally
    mirrors the fields persisted on MarketSnapshot.
    """
    symbol: str
    price: float
    volume: int
    avg_volume: float
    benchmark_change_pct: float
    volatility: float
    source: str
    quality: DataQuality
    market_timestamp: datetime   # when this price was actually true
    received_at: datetime        # when the provider handed it to us


class MarketDataProvider(ABC):
    """Contract every market data source must satisfy."""

    @abstractmethod
    def get_quote(self, symbol: str) -> MarketTick:
        """Return the latest tick available for a single symbol."""
        raise NotImplementedError

    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> dict[str, MarketTick]:
        """Return latest ticks for many symbols in one call (avoids N+1 provider calls)."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> list[str]:
        """Return instrument symbols matching a free-text query."""
        raise NotImplementedError
