# Market Pulse

**A watchlist that answers "what changed since I last looked?" instead of "what is the price now?"**

Built for the Groww Code 2026 72-hour engineering challenge.

---

## 1. Product overview

Every conventional stock watchlist shows the same thing: a table of current
prices. Market Pulse starts from a different question — the one people
actually have when they open a market app after being away for a few hours:
**"what happened, and does any of it need my attention?"**

The system remembers the market state as it was the last time you looked
(a *checkpoint*), compares it against the current state, runs the delta
through a deterministic, fully explainable scoring engine, and surfaces only
what crossed a meaningful threshold — with a plain-language reason for every
flag.

```
PREVIOUS STATE  →  CURRENT STATE  →  CHANGE DETECTION  →  ATTENTION SCORE  →  EXPLANATION  →  USER ATTENTION
```

## 2. Problem interpretation

The brief deliberately leaves several decisions open. Here is how this
project resolved each one, and why:

| Decision | Resolution | Rationale |
|---|---|---|
| What counts as a meaningful change? | A weighted, capped combination of price move vs. user threshold, volume vs. trailing average, divergence vs. a benchmark, and volatility vs. baseline (see §7) | Any single signal is noisy alone (a stock can move 3% on no volume, or spike volume on no price move); combining them with saturation curves avoids both false alarms and desensitization |
| What information to surface | Score, direction, magnitude, and *reasons* — never a raw firehose of every field | The product's whole thesis is attention triage; showing everything defeats the point |
| How state persists | Server-side, Postgres-backed checkpoints and sessions — never localStorage | A watchlist that doesn't survive a new device isn't a real product |
| How to handle stale/delayed/conflicting data | An explicit `DataQuality` enum on every market snapshot, always surfaced in the UI and folded into the score's reasons | Silently showing stale data as live is worse than showing nothing |
| How the system scales | Indexed, append-only snapshot ledger; idempotent change-event computation; no fan-out microservices | At 10k users / 100 stocks this is an I/O and indexing problem, not a distributed-systems problem |
| Where simplicity beats complexity | One Postgres database, one FastAPI process, one React SPA — a modular monolith | Splitting this into microservices before there's a scaling reason to would be pure overhead |

## 3. Architecture

Modular monolith. One deployable backend, one frontend, one database. Code
is organized by concern, not by artificial service boundaries.

```mermaid
flowchart LR
    subgraph Client
        FE[React + TS + Vite SPA]
    end
    subgraph Backend [FastAPI Modular Monolith]
        AUTH[auth router]
        WL[watchlists router]
        ST[stocks router]
        PREF[preferences router]
        SVC[services.py<br/>checkpoint / change / score orchestration]
        ENG[engine/change_engine.py<br/>deterministic scoring]
        PROV[market_data/<br/>MarketDataProvider interface]
        MOCK[MockMarketDataProvider]
    end
    DB[(PostgreSQL)]

    FE -->|HTTPS + session cookie| AUTH
    FE --> WL
    FE --> ST
    FE --> PREF
    WL --> SVC
    ST --> SVC
    SVC --> ENG
    SVC --> PROV
    PROV --> MOCK
    AUTH --> DB
    SVC --> DB
```

Swapping the mock provider for a real vendor later means implementing one
new class against `MarketDataProvider` and changing one dependency-injection
line in `app/deps.py` — nothing else in the codebase imports the mock
provider directly.

## 4. Data flow: "You Were Away"

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant DB as Postgres
    participant MP as MarketDataProvider

    U->>FE: Opens Market Pulse
    FE->>API: GET /watchlists/{id}/attention-summary
    API->>DB: Load last checkpoint (snapshot refs)
    API->>MP: get_quotes(symbols, steps)
    MP-->>API: deterministic ticks
    API->>DB: Persist new MarketSnapshot rows
    API->>API: compute_change_for_instrument (per symbol)
    API->>API: score_change() → attention + reasons
    API->>DB: Persist ChangeEvent + AttentionScore (idempotent)
    API-->>FE: YouWereAway + top changes + unchanged
    FE-->>U: Renders hero, radar, change cards
    Note over FE,API: ~4s after render, frontend fires<br/>POST /checkpoint to mark "now" as reviewed
```

## 5. Database schema

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ WATCHLISTS : owns
    USERS ||--|| USER_PREFERENCES : has
    WATCHLISTS ||--o{ WATCHLIST_ITEMS : contains
    WATCHLISTS ||--o{ USER_CHECKPOINTS : has
    WATCHLISTS ||--o{ CHANGE_EVENTS : has
    INSTRUMENTS ||--o{ WATCHLIST_ITEMS : referenced_by
    INSTRUMENTS ||--o{ MARKET_SNAPSHOTS : has
    USER_CHECKPOINTS ||--o{ CHANGE_EVENTS : anchors
    CHANGE_EVENTS ||--|| ATTENTION_SCORES : scored_by
    MARKET_SNAPSHOTS ||--o{ CHANGE_EVENTS : "previous / current"

    USERS {
        string id PK
        string email UK
        string password_hash
        bool onboarded
    }
    SESSIONS {
        string id PK
        string token UK
        string user_id FK
        datetime expires_at
        bool revoked
    }
    WATCHLISTS {
        string id PK
        string user_id FK
        string name
    }
    INSTRUMENTS {
        string id PK
        string symbol UK
        string name
        float base_price
    }
    WATCHLIST_ITEMS {
        string id PK
        string watchlist_id FK
        string instrument_id FK
        float price_threshold_pct
    }
    MARKET_SNAPSHOTS {
        string id PK
        string instrument_id FK
        float price
        int volume
        float avg_volume
        float benchmark_change_pct
        float volatility
        string quality
        datetime market_timestamp
        datetime received_at
    }
    USER_CHECKPOINTS {
        string id PK
        string user_id FK
        string watchlist_id FK
        json snapshot_refs
        datetime checked_at
    }
    CHANGE_EVENTS {
        string id PK
        string watchlist_id FK
        string instrument_id FK
        string checkpoint_id FK
        float price_change_pct
        float volume_ratio
        float benchmark_divergence_pct
    }
    ATTENTION_SCORES {
        string id PK
        string change_event_id FK
        float total_score
        string severity
        json reasons
    }
    USER_PREFERENCES {
        string id PK
        string user_id FK
        float price_threshold_pct
        float volume_spike_multiplier
    }
```

`market_snapshots` is **append-only** — it is never updated or deleted for a
given instrument, only inserted into. This makes it simultaneously an audit
log, a time series, and the source of truth for both the "since last visit"
comparison and the "recent momentum" comparison used on the live radar.

## 6. API overview

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account, start session |
| POST | `/auth/login` | Start session |
| POST | `/auth/logout` | Revoke session |
| GET | `/me` | Current user |
| POST | `/me/complete-onboarding` | Flip onboarding flag *(addition, see §11)* |
| GET/POST | `/watchlists` | List / create watchlists |
| PATCH/DELETE | `/watchlists/{id}` | Rename / delete |
| POST/DELETE | `/watchlists/{id}/stocks[/{symbol}]` | Add / remove a symbol |
| GET | `/stocks/search` | Search the instrument universe |
| GET | `/watchlists/{id}/market-state` | Live radar view (tick-over-tick attention) |
| GET | `/watchlists/{id}/changes` | Change list vs. last checkpoint |
| GET | `/watchlists/{id}/attention-summary` | "You Were Away" payload |
| POST | `/watchlists/{id}/checkpoint` | Explicitly mark current state as reviewed |
| POST | `/watchlists/{id}/simulate` | Advance the mock market one tick *(addition, see §11)* |
| GET | `/stocks/{symbol}/change-story` | Full Change Story incl. timeline |
| GET/PATCH | `/preferences` | Threshold tuning |
| GET | `/health` | Liveness |

Full interactive docs are served by FastAPI at `/docs` once the backend is running.

## 7. The meaningful-change engine

Deterministic and rule-based — **no LLM decides financial importance**.
Four independently-explainable components, each capped, summed, and mapped
to a severity band:

| Component | Range | Trigger |
|---|---|---|
| Price movement | 0–40 | Saturates at 2× the user's price threshold |
| Volume anomaly | 0–25 | Saturates at the user's volume-spike multiplier |
| Benchmark divergence | 0–20 | Saturates at 2× the benchmark-divergence threshold |
| Volatility change | 0–15 | Saturates once volatility doubles vs. baseline |

```
0–29   NORMAL
30–49  LOW
50–69  MODERATE
70–84  HIGH
85–100 CRITICAL
```

Every score is returned with the same numbers that produced it, turned into
plain sentences ("Price moved 3.24% up, exceeding your 2.0% threshold") —
there is no separate explanation step that could drift from the math, and no
claim is ever made about future price movement.

## 8. Data-quality handling

Every `MarketSnapshot` carries a `quality` field: `LIVE`, `DELAYED`,
`STALE`, or `UNAVAILABLE`, plus `market_timestamp` (when the price was true)
separate from `received_at` (when we stored it). The frontend never
collapses this distinction — a `STALE` badge is shown next to the price
everywhere it appears, and the scoring engine always appends a caveat
reason regardless of score when quality isn't `LIVE`. Silently presenting
stale data as live was treated as a correctness bug, not a display nicety.

## 9. Scalability notes

At the stated target (10k users, 100 stocks/watchlist):

- Every foreign key used in a hot-path query is indexed (`watchlist_id`,
  `instrument_id`, `(instrument_id, market_timestamp)`, `(watchlist_id, created_at)`).
- `get_watchlist_symbols` uses a single `joinedload` to avoid N+1 queries
  when fetching instruments for a watchlist.
- Change-event computation is **idempotent**: refetching the same
  checkpoint/snapshot pair reuses the existing row instead of recomputing
  and re-inserting, so refreshes and window-refocus refetches don't flood
  the table.
- The frontend uses TanStack Query for request de-duplication and caching;
  `refetchOnWindowFocus` is disabled on the summary/state queries so
  background tab switching doesn't trigger a burst of checkpoint writes.
- Nothing here requires a queue, a cache layer, or a second database. Those
  would be reasonable next additions past this scale, not at it.

## 10. Security

- Passwords hashed with bcrypt (via `passlib`).
- Auth is a server-side session token in an `httpOnly`, `SameSite=Lax`
  cookie — not a JWT in localStorage, so a session can be revoked instantly
  on logout and can't be read by client-side JS/XSS.
- CORS restricted to the configured frontend origin(s).
- All input validated by Pydantic; ownership checked on every watchlist
  route (`user_id` filter, not just `id`) to prevent IDOR.
- No secrets in source; everything sensitive comes from environment
  variables (see `.env.example`).
- SQLAlchemy ORM throughout — no raw string-interpolated SQL.

## 11. Deliberate additions beyond the literal spec

Two things were added because the required demo flow cannot work without them:

1. **`POST /watchlists/{id}/simulate`** — the brief describes a "Simulate
   Market Update" button but the literal endpoint list doesn't include one.
   Without it, there is no way to advance the mock market on demand.
2. **`POST /me/complete-onboarding`** — a minimal flag-flip so the
   Onboarding page has somewhere to record "this user has set up a
   watchlist," gating the `/pulse` route.

Both are documented here rather than silently added.

## 12. Setup instructions

### Option A — Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs at `/docs`)
- Postgres: localhost:5432 (user/pass/db: `marketpulse`)

The backend container runs Alembic migrations and seeds the demo account
automatically on startup, and waits for Postgres's healthcheck before
starting (`depends_on: condition: service_healthy`).

### Option B — Local dev

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://marketpulse:marketpulse@localhost:5432/marketpulse
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

`scripts/dev-setup.sh` wraps the backend half of this.

## 13. Demo credentials

```
Email:    demo@growwpulse.app
Password: Demo@12345
```

Seeded with 12 instruments in one watchlist, pre-baked into exactly the mix
described in the brief: 3 high-attention, 2 moderate, 2 low, 3 unchanged,
1 stale, 1 delayed — so the "You Were Away" story is real the moment you log
in, with zero manual setup.

## 14. Testing

`backend/tests/` (pytest, run against an in-memory SQLite DB so the suite
has no external dependencies):

- `test_auth.py` — register, duplicate email, login/logout, session revocation
- `test_watchlist.py` — CRUD, ownership isolation, symbol validation, bootstrap
- `test_change_detection.py` — checkpoint creation, simulate → detectable
  change, manual checkpoint resets the baseline, Change Story timeline,
  persistence and idempotency of change events/attention scores
- `test_data_quality.py` — stale/delayed flagging never silently hidden, and
  surfaced in Change Story reasons
- `test_preferences_and_errors.py` — preference updates, validation errors,
  auth-required routes, 404s

Run with:

```bash
cd backend
pytest -v
```

> **Honesty note on verification.** This backend was authored and
> hand-verified inside a sandboxed environment **without network access or
> pre-installed FastAPI/SQLAlchemy/Postgres**, so the pytest suite above and
> the live server itself could not be executed inside that environment. The
> two purely algorithmic cores — the mock market data provider and the
> attention-scoring engine — *were* extracted and run standalone (no
> framework dependencies) during development, which caught and fixed two
> real bugs: a provider step-simulation bug that caused price jumps to
> re-fire on every tick instead of once, and a scoring miscalibration that
> under-scored the brief's own worked example. Frontend code was
> type-checked with a local TypeScript compiler pass, which caught two real
> type errors (missing `FormEvent` import, missing CSS module declaration).
> Everything else — the full request/response cycle, Alembic migrations
> against real Postgres, and Docker Compose orchestration — is written
> carefully and I stand behind the design, but you should run
> `docker compose up --build` and `pytest` yourself as the final check
> before submitting.

## 15. Engineering tradeoffs

- **SQLite in tests vs. Postgres in production**: chosen for a
  zero-dependency test suite. Nothing in the schema uses Postgres-only
  features, so this is safe, but it does mean the test suite can't catch a
  Postgres-specific migration issue — that's what `docker compose up` +
  manual smoke-testing is for.
- **Checkpoint-on-view-with-delay** rather than checkpoint-on-every-GET:
  keeps `GET /attention-summary` a pure, idempotent read (good REST
  hygiene, safe to refetch) while still making "returning to the app" a
  real, persisted event. The cost is a small window (a few seconds) where a
  very fast visit-and-leave might not get marked as reviewed.
- **In-memory scenario assignment in the mock provider** rather than a
  database column: keeps the provider fully swappable and stateless from
  the DB's perspective, at the cost of demo scenarios being hardcoded by
  symbol rather than configurable per-watchlist.
- **No message queue / cache layer**: deliberately omitted at this scale
  (see §9); would be the first addition past ~10x the stated target.

## 16. Future improvements

- A real `MarketDataProvider` implementation (NSE/BSE feed or a paid
  vendor), swapped in via one line in `app/deps.py`.
- WebSocket push for live radar updates instead of polling.
- Per-sector or per-portfolio aggregate attention ("your Banking stocks are
  quiet, your IT stocks are loud").
- Configurable notification channels (email/push) gated by
  `notify_on_critical_only`.
- Multi-watchlist support in the frontend UI (the backend already supports
  multiple watchlists per user; the frontend currently always operates on
  the first one for simplicity).

---

*Market Pulse is an information and monitoring tool. It explains what
changed and why it crossed a threshold — it does not predict future price
movement and is not investment advice.*
