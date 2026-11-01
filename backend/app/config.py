"""
Central configuration for Market Pulse backend.

All configuration is sourced from environment variables so that no secrets
live in source code. See .env.example at the project root for the full list.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---
    APP_NAME: str = "Market Pulse"
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg2://marketpulse:marketpulse@localhost:5432/marketpulse"
    )

    # --- Auth / Sessions ---
    SESSION_TOKEN_BYTES: int = 32
    SESSION_TTL_HOURS: int = 24 * 7  # 7 days
    COOKIE_NAME: str = "mp_session"
    COOKIE_SECURE: bool = False  # set True behind HTTPS in production

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:9995"]

    # --- Market data / change engine tuning ---
    DEFAULT_PRICE_THRESHOLD_PCT: float = 2.0
    VOLUME_SPIKE_MULTIPLIER: float = 2.0
    STALE_DATA_SECONDS: int = 900       # 15 minutes -> considered stale
    DELAYED_DATA_SECONDS: int = 120     # 2 minutes -> considered delayed


@lru_cache
def get_settings() -> Settings:
    return Settings()
