"""
MockMarketDataProvider.

Generates deterministic, reproducible market data without any external API
key. "Deterministic" here means: given the same symbol and the same *step*
(how many times we've generated data for that symbol before), you always get
the same tick. This is what makes the demo video look consistent on every
run, while still allowing "Simulate Market Update" to advance the story by
incrementing the step.

Each demo symbol is assigned a fixed SCENARIO so the seeded demo account
always reproduces the exact mix the challenge asks for:
3 high-attention, 2 moderate, 2 low, 3 unchanged, 1 stale, 1 delayed.
Any symbol not in the map falls back to a hash-based "mostly normal" scenario
so ad-hoc searched stocks still behave sensibly.
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone

from app.market_data.provider import MarketDataProvider, MarketTick
from app.models import DataQuality

# symbol -> (name, sector, base_price)
INSTRUMENT_UNIVERSE: dict[str, tuple[str, str, float]] = {
    "RELIANCE": ("Reliance Industries Ltd", "Energy", 1421.00),
    "TCS":      ("Tata Consultancy Services", "IT", 3845.50),
    "HDFCBANK": ("HDFC Bank Ltd", "Banking", 1652.30),
    "INFY":     ("Infosys Ltd", "IT", 1489.75),
    "ICICIBANK":("ICICI Bank Ltd", "Banking", 1198.40),
    "TATAMOTORS":("Tata Motors Ltd", "Auto", 962.15),
    "SBIN":     ("State Bank of India", "Banking", 812.60),
    "ITC":      ("ITC Ltd", "FMCG", 468.90),
    "BHARTIARTL":("Bharti Airtel Ltd", "Telecom", 1543.20),
    "ADANIENT": ("Adani Enterprises Ltd", "Diversified", 2874.00),
    "WIPRO":    ("Wipro Ltd", "IT", 542.10),
    "LT":       ("Larsen & Toubro Ltd", "Infra", 3612.80),
    "MARUTI":   ("Maruti Suzuki India Ltd", "Auto", 12480.00),
    "SUNPHARMA":("Sun Pharmaceutical Ltd", "Pharma", 1789.30),
    "ASIANPAINT":("Asian Paints Ltd", "FMCG", 2954.60),
}

# Explicit demo scenarios so the seeded demo account always tells the exact
# story described in the challenge brief.
SCENARIOS: dict[str, str] = {
    "RELIANCE":   "meaningful_up",
    "ADANIENT":   "meaningful_down",
    "TATAMOTORS": "volume_spike",       # counts as HIGH attention (volume anomaly)
    "ICICIBANK":  "moderate_up",
    "BHARTIARTL": "moderate_down",
    "SBIN":       "low_move",
    "WIPRO":      "low_move",
    "TCS":        "unchanged",
    "INFY":       "unchanged",
    "LT":         "unchanged",
    "ITC":        "stale",
    "MARUTI":     "delayed",
    "SUNPHARMA":  "normal",
    "ASIANPAINT": "normal",
}


def _fallback_scenario(symbol: str) -> str:
    """Ad-hoc symbols (e.g. from search) get a mostly-quiet, hash-stable scenario."""
    bucket = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 10
    if bucket == 0:
        return "moderate_up"
    if bucket == 1:
        return "low_move"
    return "normal"


def _rng_for(symbol: str, step: int) -> random.Random:
    seed = int(hashlib.sha256(f"{symbol}:{step}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _benchmark_move_for_step(step: int) -> float:
    """A shared 'index' move for the given step, so benchmark divergence is meaningful."""
    rng = random.Random(step * 7919 + 17)
    return round(rng.uniform(-0.6, 0.6), 3)


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic, in-memory, offline market data provider."""

    def __init__(self) -> None:
        self._universe = INSTRUMENT_UNIVERSE

    def search(self, query: str) -> list[str]:
        q = query.strip().upper()
        if not q:
            return list(self._universe.keys())
        return [
            sym for sym, (name, *_rest) in self._universe.items()
            if q in sym or q in name.upper()
        ]

    def get_quote(self, symbol: str) -> MarketTick:
        return self.get_quotes([symbol])[symbol]

    def get_quotes(self, symbols: list[str], steps: dict[str, int] | None = None) -> dict[str, MarketTick]:
        """
        steps: optional map of symbol -> how many prior snapshots exist for it.
        Callers (the market service) pass this in based on DB history so the
        simulation is reproducible even across backend restarts.
        """
        steps = steps or {}
        now = datetime.now(timezone.utc)
        out: dict[str, MarketTick] = {}

        for symbol in symbols:
            base_name, sector, base_price = self._universe.get(
                symbol, (symbol.title(), "Unknown", 1000.0)
            )
            step = steps.get(symbol, 0)
            scenario = SCENARIOS.get(symbol) or _fallback_scenario(symbol)
            benchmark_pct = _benchmark_move_for_step(step)
            rng = _rng_for(symbol, step)

            out[symbol] = self._simulate(
                symbol=symbol, base_price=base_price, step=step,
                scenario=scenario, benchmark_pct=benchmark_pct, rng=rng, now=now,
            )
        return out

    # -- scenario simulation -------------------------------------------------

    def _simulate(self, *, symbol, base_price, step, scenario, benchmark_pct, rng, now) -> MarketTick:
        avg_volume = base_price * 8_000 + rng.uniform(0, 50_000)  # arbitrary but stable-ish baseline

        # Cumulative walk up to `step`, computed the SAME way every time it is
        # requested (each step's move depends only on (symbol, that step) --
        # never on which step the caller originally asked for). That is what
        # makes this both deterministic (re-asking for step 4 always gives the
        # same price) and monotonic (step 4 always builds on step 3, it never
        # re-applies an earlier jump).
        #
        # s == 0  -> baseline tick ("what the user saw when they last checked")
        # s == 1  -> the scripted, story-defining move for this scenario
        # s >= 2  -> gentle continued drift, so repeated "Simulate Market
        #            Update" clicks keep the story moving without re-firing
        #            the same big headline move over and over.
        price = base_price
        volume_ratio = 1.0
        volatility = 0.6
        quality = DataQuality.LIVE
        market_ts = now

        for s in range(step + 1):
            r = _rng_for(symbol, s)
            headline = (s == 1)  # the one step where the scripted move fires

            if scenario == "meaningful_up":
                pct = 3.2 if headline else (0.0 if s == 0 else r.uniform(-0.3, 0.3))
                volume_ratio = 2.4 if headline else (1.1 if s > 1 else 1.0)
                volatility = 1.8 if headline else (1.0 if s > 1 else 0.6)
            elif scenario == "meaningful_down":
                pct = -3.6 if headline else (0.0 if s == 0 else r.uniform(-0.3, 0.3))
                volume_ratio = 2.7 if headline else (1.1 if s > 1 else 1.0)
                volatility = 2.0 if headline else (1.0 if s > 1 else 0.6)
            elif scenario == "volume_spike":
                pct = 0.0 if s == 0 else r.uniform(-0.4, 0.6)
                volume_ratio = 3.1 if headline else (1.3 if s > 1 else 1.0)
                volatility = 1.1 if s >= 1 else 0.6
            elif scenario == "moderate_up":
                pct = 1.6 if headline else (0.0 if s == 0 else r.uniform(-0.2, 0.2))
                volume_ratio = 1.6 if headline else (1.1 if s > 1 else 1.0)
                volatility = 1.0 if s >= 1 else 0.6
            elif scenario == "moderate_down":
                pct = -1.8 if headline else (0.0 if s == 0 else r.uniform(-0.2, 0.2))
                volume_ratio = 1.5 if headline else (1.05 if s > 1 else 1.0)
                volatility = 1.1 if s >= 1 else 0.6
            elif scenario == "low_move":
                pct = 0.8 if headline else (0.0 if s == 0 else r.uniform(-0.15, 0.15))
                volume_ratio = 1.2
                volatility = 0.7 if s >= 1 else 0.5
            elif scenario == "unchanged":
                pct = 0.0 if s == 0 else r.uniform(-0.1, 0.1)
                volume_ratio = 0.95 + r.uniform(-0.1, 0.1)
                volatility = 0.4
            elif scenario == "stale":
                pct = 0.0
                volume_ratio = 1.0
                volatility = 0.3
            elif scenario == "delayed":
                pct = 0.0 if s == 0 else r.uniform(-0.5, 0.9)
                volume_ratio = 1.1
                volatility = 0.8
            elif scenario == "unavailable":
                pct = 0.0
                volume_ratio = 0.0
                volatility = 0.0
            else:  # normal
                pct = 0.0 if s == 0 else r.uniform(-0.5, 0.5)
                volume_ratio = 1.0 + r.uniform(-0.15, 0.15)
                volatility = 0.6

            price = round(price * (1 + pct / 100), 2)

        if scenario == "stale":
            quality = DataQuality.STALE
            market_ts = now - timedelta(minutes=22)
        elif scenario == "delayed":
            quality = DataQuality.DELAYED
            market_ts = now - timedelta(minutes=3, seconds=20)
        elif scenario == "unavailable":
            quality = DataQuality.UNAVAILABLE
            market_ts = now - timedelta(hours=2)
        else:
            quality = DataQuality.LIVE
            market_ts = now

        volume = max(1, int(avg_volume * volume_ratio))

        return MarketTick(
            symbol=symbol,
            price=price,
            volume=volume,
            avg_volume=round(avg_volume, 2),
            benchmark_change_pct=benchmark_pct,
            volatility=round(volatility, 3),
            source="mock",
            quality=quality,
            market_timestamp=market_ts,
            received_at=now,
        )
