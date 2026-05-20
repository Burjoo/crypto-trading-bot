"""
Application configuration using Pydantic Settings.
All settings are loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "CryptoBot Pro"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── Security ────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-very-long-random-secret-key-min-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AES encryption key for exchange API keys (Fernet — must be 32 url-safe base64 bytes)
    ENCRYPTION_KEY: Optional[str] = None

    # ─── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cryptobot:cryptobot_secret@localhost:5432/cryptobot"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ─── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # ─── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    # ─── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_ALERTS_ENABLED: bool = False

    # ─── Exchange Defaults ───────────────────────────────────────────────────
    SUPPORTED_EXCHANGES: List[str] = ["binance", "bybit", "coinbasepro"]
    DEFAULT_QUOTE_CURRENCY: str = "USDT"
    PAPER_TRADING_BALANCE: float = 10_000.0

    # ─── Trading Engine ──────────────────────────────────────────────────────
    MAX_BOTS_PER_USER: int = 10
    BOT_TICK_INTERVAL_SECONDS: int = 5
    MAX_POSITION_SIZE_PCT: float = 0.10   # 10% of portfolio per trade
    DEFAULT_RISK_PER_TRADE_PCT: float = 0.01  # 1% risk per trade

    # ─── Backtesting ─────────────────────────────────────────────────────────
    BACKTEST_MAX_CANDLES: int = 10_000
    BACKTEST_DEFAULT_COMMISSION: float = 0.001  # 0.1%

    # ─── Sentry ──────────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None

    # ─── Admin ───────────────────────────────────────────────────────────────
    FIRST_SUPERUSER_EMAIL: str = "admin@cryptobot.pro"
    FIRST_SUPERUSER_PASSWORD: str = "changeme123!"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — instantiated once per process."""
    return Settings()


settings = get_settings()
