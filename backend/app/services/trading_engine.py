"""
Modular Trading Engine.

Supports: Moving Average Crossover, RSI, MACD, Breakout strategies.
Each strategy is a class implementing the BaseStrategy interface.
The TradingEngine orchestrates bot lifecycle, signals, and order execution.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class OHLCV:
    """Single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    """Trading signal produced by a strategy."""
    action: str          # "buy", "sell", "hold"
    symbol: str
    price: float
    confidence: float    # 0.0 – 1.0
    reason: str          # human-readable explanation
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


@dataclass
class BotContext:
    """Runtime context passed to each strategy tick."""
    bot_id: str
    symbol: str
    timeframe: str
    candles: pd.DataFrame      # columns: open, high, low, close, volume
    current_price: float
    position: Optional[dict]   # current open position or None
    paper_balance: float
    params: dict               # strategy-specific parameters


# ─── Base Strategy ────────────────────────────────────────────────────────────

class BaseStrategy(ABC):
    """
    All strategies implement this interface.
    `generate_signal` receives processed candle data and returns a Signal.
    """

    name: str = "base"
    default_params: dict = {}

    def __init__(self, params: dict | None = None):
        self.params = {**self.default_params, **(params or {})}

    @abstractmethod
    def generate_signal(self, ctx: BotContext) -> Signal:
        ...

    def _require_candles(self, df: pd.DataFrame, n: int) -> bool:
        return len(df) >= n


# ─── Moving Average Crossover ─────────────────────────────────────────────────

class MovingAverageCrossover(BaseStrategy):
    """
    Classic golden cross / death cross strategy.
    BUY  when fast EMA crosses above slow EMA.
    SELL when fast EMA crosses below slow EMA.
    """

    name = "ma_crossover"
    default_params = {
        "fast_period": 9,
        "slow_period": 21,
        "signal_period": 5,   # confirmation candles
        "ma_type": "ema",     # "ema" | "sma"
    }

    def generate_signal(self, ctx: BotContext) -> Signal:
        df = ctx.candles
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]

        if not self._require_candles(df, slow + 5):
            return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "Not enough candles")

        ma_fn = df["close"].ewm if self.params["ma_type"] == "ema" else None

        if self.params["ma_type"] == "ema":
            fast_ma = df["close"].ewm(span=fast, adjust=False).mean()
            slow_ma = df["close"].ewm(span=slow, adjust=False).mean()
        else:
            fast_ma = df["close"].rolling(fast).mean()
            slow_ma = df["close"].rolling(slow).mean()

        prev_fast, prev_slow = fast_ma.iloc[-2], slow_ma.iloc[-2]
        curr_fast, curr_slow = fast_ma.iloc[-1], slow_ma.iloc[-1]

        diff_pct = abs(curr_fast - curr_slow) / curr_slow * 100
        confidence = min(diff_pct / 2.0, 1.0)  # scale to [0, 1]

        # Golden cross
        if prev_fast <= prev_slow and curr_fast > curr_slow and not ctx.position:
            return Signal(
                action="buy",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"Golden cross: EMA{fast} crossed above EMA{slow}",
                metadata={"fast_ma": curr_fast, "slow_ma": curr_slow},
            )

        # Death cross
        if prev_fast >= prev_slow and curr_fast < curr_slow and ctx.position:
            return Signal(
                action="sell",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"Death cross: EMA{fast} crossed below EMA{slow}",
                metadata={"fast_ma": curr_fast, "slow_ma": curr_slow},
            )

        return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "No crossover detected")


# ─── RSI Strategy ─────────────────────────────────────────────────────────────

class RSIStrategy(BaseStrategy):
    """
    RSI mean-reversion strategy.
    BUY  when RSI drops below oversold threshold and recovers.
    SELL when RSI rises above overbought threshold and turns down.
    """

    name = "rsi"
    default_params = {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "confirmation_candles": 2,
    }

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.finfo(float).eps)
        return 100 - (100 / (1 + rs))

    def generate_signal(self, ctx: BotContext) -> Signal:
        df = ctx.candles
        period = self.params["rsi_period"]

        if not self._require_candles(df, period + 5):
            return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "Not enough candles")

        rsi = self._rsi(df["close"], period)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        oversold = self.params["oversold"]
        overbought = self.params["overbought"]

        # Oversold recovery → buy
        if prev_rsi < oversold and current_rsi >= oversold and not ctx.position:
            confidence = (oversold - min(prev_rsi, oversold)) / oversold
            return Signal(
                action="buy",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=min(confidence, 1.0),
                reason=f"RSI oversold recovery: {current_rsi:.1f} crossed above {oversold}",
                metadata={"rsi": current_rsi},
            )

        # Overbought rejection → sell
        if prev_rsi > overbought and current_rsi <= overbought and ctx.position:
            confidence = (min(prev_rsi, 100) - overbought) / (100 - overbought)
            return Signal(
                action="sell",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=min(confidence, 1.0),
                reason=f"RSI overbought rejection: {current_rsi:.1f} crossed below {overbought}",
                metadata={"rsi": current_rsi},
            )

        return Signal("hold", ctx.symbol, ctx.current_price, 0.0, f"RSI neutral: {current_rsi:.1f}")


# ─── MACD Strategy ────────────────────────────────────────────────────────────

class MACDStrategy(BaseStrategy):
    """
    MACD signal line crossover strategy.
    BUY  when MACD line crosses above signal line (bullish momentum).
    SELL when MACD line crosses below signal line (bearish momentum).
    """

    name = "macd"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "histogram_threshold": 0.0,
    }

    def generate_signal(self, ctx: BotContext) -> Signal:
        df = ctx.candles
        fp = self.params["fast_period"]
        sp = self.params["slow_period"]
        sig_p = self.params["signal_period"]

        if not self._require_candles(df, sp + sig_p + 5):
            return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "Not enough candles")

        fast_ema = df["close"].ewm(span=fp, adjust=False).mean()
        slow_ema = df["close"].ewm(span=sp, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=sig_p, adjust=False).mean()
        histogram = macd_line - signal_line

        curr_macd, curr_sig = macd_line.iloc[-1], signal_line.iloc[-1]
        prev_macd, prev_sig = macd_line.iloc[-2], signal_line.iloc[-2]
        curr_hist = histogram.iloc[-1]

        confidence = min(abs(curr_hist) / (abs(curr_sig) + 1e-10), 1.0)

        # Bullish crossover
        if prev_macd <= prev_sig and curr_macd > curr_sig and curr_macd < 0 and not ctx.position:
            return Signal(
                action="buy",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"MACD bullish crossover (histogram: {curr_hist:.4f})",
                metadata={"macd": curr_macd, "signal": curr_sig, "histogram": curr_hist},
            )

        # Bearish crossover
        if prev_macd >= prev_sig and curr_macd < curr_sig and curr_macd > 0 and ctx.position:
            return Signal(
                action="sell",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"MACD bearish crossover (histogram: {curr_hist:.4f})",
                metadata={"macd": curr_macd, "signal": curr_sig, "histogram": curr_hist},
            )

        return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "No MACD crossover")


# ─── Breakout Strategy ────────────────────────────────────────────────────────

class BreakoutStrategy(BaseStrategy):
    """
    Support/Resistance breakout strategy.
    BUY  on confirmed break above resistance with volume confirmation.
    SELL on confirmed break below support with volume confirmation.
    """

    name = "breakout"
    default_params = {
        "lookback_period": 20,
        "volume_multiplier": 1.5,   # Volume must be N× the average
        "breakout_threshold_pct": 0.5,
    }

    def generate_signal(self, ctx: BotContext) -> Signal:
        df = ctx.candles
        lookback = self.params["lookback_period"]

        if not self._require_candles(df, lookback + 5):
            return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "Not enough candles")

        window = df.iloc[-(lookback + 1):-1]  # exclude current candle
        resistance = window["high"].max()
        support = window["low"].min()
        avg_volume = window["volume"].mean()

        current = df.iloc[-1]
        vol_multiplier = current["volume"] / (avg_volume + 1e-10)
        threshold = self.params["breakout_threshold_pct"] / 100
        vol_ok = vol_multiplier >= self.params["volume_multiplier"]

        # Resistance breakout
        if (current["close"] > resistance * (1 + threshold)
                and vol_ok
                and not ctx.position):
            confidence = min((current["close"] / resistance - 1) * 50, 1.0)
            return Signal(
                action="buy",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"Breakout above resistance {resistance:.4f} (vol: {vol_multiplier:.1f}×)",
                metadata={"resistance": resistance, "support": support, "vol_ratio": vol_multiplier},
            )

        # Support breakdown
        if (current["close"] < support * (1 - threshold)
                and vol_ok
                and ctx.position):
            confidence = min((1 - current["close"] / support) * 50, 1.0)
            return Signal(
                action="sell",
                symbol=ctx.symbol,
                price=ctx.current_price,
                confidence=confidence,
                reason=f"Breakdown below support {support:.4f} (vol: {vol_multiplier:.1f}×)",
                metadata={"resistance": resistance, "support": support, "vol_ratio": vol_multiplier},
            )

        return Signal(
            "hold", ctx.symbol, ctx.current_price, 0.0,
            f"Price within range [{support:.4f}, {resistance:.4f}]"
        )


# ─── Strategy Registry ────────────────────────────────────────────────────────

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "ma_crossover": MovingAverageCrossover,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "breakout": BreakoutStrategy,
}


def get_strategy(strategy_type: str, params: dict | None = None) -> BaseStrategy:
    """Instantiate a strategy by type name."""
    cls = STRATEGY_REGISTRY.get(strategy_type)
    if not cls:
        raise ValueError(f"Unknown strategy type: {strategy_type!r}. "
                         f"Available: {list(STRATEGY_REGISTRY)}")
    return cls(params)


# ─── Risk Manager ─────────────────────────────────────────────────────────────

class RiskManager:
    """
    Validates and sizes positions according to risk rules.
    Calculates stop-loss, take-profit, and position sizes.
    """

    def calculate_position_size(
        self,
        account_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        """
        Calculate position size (quantity) using the fixed fractional method.
        risk_pct: percentage of account to risk (e.g. 1.0 = 1%)
        """
        risk_amount = account_balance * (risk_pct / 100)
        price_risk = abs(entry_price - stop_loss_price)
        if price_risk == 0:
            return 0.0
        quantity = risk_amount / price_risk
        return round(quantity, 6)

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        stop_loss_pct: float,
    ) -> float:
        """Calculate stop-loss price from percentage."""
        if side == "buy":
            return entry_price * (1 - stop_loss_pct / 100)
        return entry_price * (1 + stop_loss_pct / 100)

    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        take_profit_pct: float,
    ) -> float:
        """Calculate take-profit price from percentage."""
        if side == "buy":
            return entry_price * (1 + take_profit_pct / 100)
        return entry_price * (1 - take_profit_pct / 100)

    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> float:
        """Return the risk/reward ratio."""
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
        if risk == 0:
            return 0.0
        return round(reward / risk, 2)

    def check_max_daily_loss(
        self,
        daily_pnl: float,
        max_daily_loss: float,
    ) -> bool:
        """Returns True if trading should be halted (max daily loss exceeded)."""
        return daily_pnl <= -abs(max_daily_loss)

    def trailing_stop_price(
        self,
        side: str,
        high_water_mark: float,
        trail_pct: float,
    ) -> float:
        """Calculate trailing stop price from the high-water mark."""
        if side == "buy":
            return high_water_mark * (1 - trail_pct / 100)
        return high_water_mark * (1 + trail_pct / 100)
