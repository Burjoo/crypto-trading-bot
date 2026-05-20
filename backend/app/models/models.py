"""
SQLAlchemy ORM models for all database tables.
Using declarative base with async support.
"""
import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    PREMIUM = "premium"


class ExchangeName(str, enum.Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    COINBASEPRO = "coinbasepro"


class BotStatus(str, enum.Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class TradeSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class StrategyType(str, enum.Enum):
    MA_CROSSOVER = "ma_crossover"
    RSI = "rsi"
    MACD = "macd"
    BREAKOUT = "breakout"
    CUSTOM = "custom"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class AlertType(str, enum.Enum):
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_ERROR = "bot_error"
    DAILY_SUMMARY = "daily_summary"
    MAX_LOSS_REACHED = "max_loss_reached"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(50))
    telegram_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    exchanges: Mapped[list["Exchange"]] = relationship("Exchange", back_populates="user", cascade="all, delete-orphan")
    bots: Mapped[list["Bot"]] = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="user")
    journal_entries: Mapped[list["JournalEntry"]] = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    settings: Mapped[Optional["UserSettings"]] = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


# ─── Exchange ─────────────────────────────────────────────────────────────────

class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[ExchangeName] = mapped_column(Enum(ExchangeName), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_api_secret: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_passphrase: Mapped[Optional[str]] = mapped_column(Text)  # Coinbase Pro
    is_paper_trading: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="exchanges")
    bots: Mapped[list["Bot"]] = relationship("Bot", back_populates="exchange")

    __table_args__ = (
        UniqueConstraint("user_id", "name", "label", name="uq_user_exchange_label"),
    )


# ─── Strategy ─────────────────────────────────────────────────────────────────

class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # Strategy marketplace
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bots: Mapped[list["Bot"]] = relationship("Bot", back_populates="strategy")


# ─── Bot ──────────────────────────────────────────────────────────────────────

class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange_id: Mapped[str] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. BTC/USDT
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")  # 1m, 5m, 15m, 1h, 4h, 1d
    status: Mapped[BotStatus] = mapped_column(Enum(BotStatus), default=BotStatus.STOPPED)

    # Risk settings
    position_size_usdt: Mapped[float] = mapped_column(Float, default=100.0)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=1)
    stop_loss_pct: Mapped[Optional[float]] = mapped_column(Float)
    take_profit_pct: Mapped[Optional[float]] = mapped_column(Float)
    trailing_stop_pct: Mapped[Optional[float]] = mapped_column(Float)
    max_daily_loss_usdt: Mapped[Optional[float]] = mapped_column(Float)

    # Performance counters (denormalized for speed)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)

    # Paper trading state
    paper_balance_usdt: Mapped[float] = mapped_column(Float, default=10_000.0)

    last_tick_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bots")
    exchange: Mapped["Exchange"] = relationship("Exchange", back_populates="bots")
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="bots")
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="bot")

    __table_args__ = (
        Index("ix_bots_user_status", "user_id", "status"),
    )


# ─── Trade ────────────────────────────────────────────────────────────────────

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bot_id: Mapped[Optional[str]] = mapped_column(ForeignKey("bots.id", ondelete="SET NULL"))
    exchange_id: Mapped[str] = mapped_column(ForeignKey("exchanges.id"), nullable=False)

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.MARKET)
    status: Mapped[TradeStatus] = mapped_column(Enum(TradeStatus), default=TradeStatus.OPEN)

    # Pricing
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    # Risk levels
    stop_loss_price: Mapped[Optional[float]] = mapped_column(Float)
    take_profit_price: Mapped[Optional[float]] = mapped_column(Float)

    # PnL
    pnl_usdt: Mapped[Optional[float]] = mapped_column(Float)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    commission_usdt: Mapped[float] = mapped_column(Float, default=0.0)

    # Exchange order IDs
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    is_paper_trade: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    entry_reason: Mapped[Optional[str]] = mapped_column(Text)  # Signal that triggered entry
    exit_reason: Mapped[Optional[str]] = mapped_column(Text)   # sl, tp, manual, signal

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="trades")
    bot: Mapped[Optional["Bot"]] = relationship("Bot", back_populates="trades")
    journal_entry: Mapped[Optional["JournalEntry"]] = relationship("JournalEntry", back_populates="trade", uselist=False)

    __table_args__ = (
        Index("ix_trades_user_status", "user_id", "status"),
        Index("ix_trades_user_opened", "user_id", "opened_at"),
        Index("ix_trades_symbol", "symbol"),
    )


# ─── Journal Entry ────────────────────────────────────────────────────────────

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trade_id: Mapped[Optional[str]] = mapped_column(ForeignKey("trades.id", ondelete="SET NULL"))

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    emotion: Mapped[Optional[str]] = mapped_column(String(50))   # fomo, confident, fearful, neutral
    mistakes: Mapped[Optional[str]] = mapped_column(Text)
    lessons: Mapped[Optional[str]] = mapped_column(Text)
    setup_quality: Mapped[Optional[int]] = mapped_column(Integer)  # 1-10
    tags: Mapped[list] = mapped_column(JSON, default=list)
    screenshot_urls: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="journal_entries")
    trade: Mapped[Optional["Trade"]] = relationship("Trade", back_populates="journal_entry")


# ─── Alert ────────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    sent_via_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_user_read", "user_id", "is_read"),
    )


# ─── User Settings ────────────────────────────────────────────────────────────

class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Display
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Notification preferences
    notify_trade_open: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_trade_close: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_stop_loss: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_take_profit: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_summary_time: Mapped[str] = mapped_column(String(10), default="08:00")

    # Risk defaults
    default_risk_pct: Mapped[float] = mapped_column(Float, default=1.0)
    default_stop_loss_pct: Mapped[float] = mapped_column(Float, default=2.0)
    default_take_profit_pct: Mapped[float] = mapped_column(Float, default=4.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="settings")
