"""
Vectorized Backtesting Engine.

Runs strategies on historical OHLCV data using Pandas vectorized operations.
Returns comprehensive performance metrics: Sharpe ratio, max drawdown,
win rate, average RR, equity curve, and per-trade log.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.services.trading_engine import BaseStrategy, BotContext, Signal, get_strategy

logger = logging.getLogger(__name__)


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    strategy_type: str
    strategy_params: dict
    symbol: str
    timeframe: str
    initial_capital: float = 10_000.0
    commission_pct: float = 0.1          # 0.1%
    stop_loss_pct: Optional[float] = 2.0
    take_profit_pct: Optional[float] = 4.0
    risk_per_trade_pct: float = 1.0      # % of equity risked per trade
    max_open_trades: int = 1
    slippage_pct: float = 0.05           # 0.05% slippage


@dataclass
class BacktestTrade:
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    exit_reason: str = ""
    entry_reason: str = ""


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    strategy: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float

    # Performance
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float

    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_risk_reward: float
    profit_factor: float
    expectancy_usdt: float

    # Series (for charts)
    equity_curve: list[dict]          # [{date, equity}, ...]
    drawdown_series: list[dict]       # [{date, drawdown_pct}, ...]
    trade_log: list[dict]             # per-trade detail

    # Raw trades for further analysis
    trades: list[BacktestTrade] = field(default_factory=list)


# ─── Backtesting Engine ───────────────────────────────────────────────────────

class BacktestEngine:
    """
    Event-driven backtester with vectorized signal generation.

    Workflow:
    1. Pre-compute all signals in a single pass (vectorized).
    2. Simulate order execution candle by candle (realistic fills).
    3. Apply stop-loss, take-profit, trailing stops.
    4. Calculate performance metrics on the completed trade log.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.strategy: BaseStrategy = get_strategy(
            config.strategy_type, config.strategy_params
        )

    def run(self, ohlcv_data: list[dict] | pd.DataFrame) -> BacktestResult:
        """
        Execute the backtest on the provided OHLCV data.
        ohlcv_data: list of dicts with keys: timestamp, open, high, low, close, volume
                    OR a pre-built DataFrame with those columns.
        """
        df = self._prepare_dataframe(ohlcv_data)
        if len(df) < 50:
            raise ValueError("Need at least 50 candles for a meaningful backtest")

        logger.info(
            "Starting backtest: %s | %s | %d candles",
            self.config.symbol,
            self.config.strategy_type,
            len(df),
        )

        trades, equity_curve = self._simulate(df)
        return self._compute_metrics(df, trades, equity_curve)

    # ── Private Methods ───────────────────────────────────────────────────────

    def _prepare_dataframe(self, data: list[dict] | pd.DataFrame) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = pd.DataFrame(data)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].astype(
            {"open": float, "high": float, "low": float, "close": float, "volume": float}
        )
        return df

    def _simulate(self, df: pd.DataFrame) -> tuple[list[BacktestTrade], list[float]]:
        cfg = self.config
        capital = cfg.initial_capital
        position: Optional[dict] = None
        trades: list[BacktestTrade] = []
        equity_curve: list[float] = []
        high_water_mark: float = 0.0  # for trailing stop

        for i in range(50, len(df)):
            candle = df.iloc[i]
            candle_close = float(candle["close"])
            candle_high = float(candle["high"])
            candle_low = float(candle["low"])

            # ── Check stop-loss / take-profit on open position ────────────
            if position:
                exit_price: Optional[float] = None
                exit_reason = ""
                side = position["side"]

                if side == "buy":
                    # Update high-water mark for trailing stop
                    high_water_mark = max(high_water_mark, candle_high)

                    # Check stop-loss (hit on candle low)
                    if cfg.stop_loss_pct and candle_low <= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        exit_reason = "stop_loss"

                    # Check take-profit (hit on candle high)
                    elif cfg.take_profit_pct and candle_high >= position["take_profit"]:
                        exit_price = position["take_profit"]
                        exit_reason = "take_profit"

                    # Check trailing stop
                    elif position.get("trailing_stop"):
                        trail_stop = high_water_mark * (1 - cfg.stop_loss_pct / 100)
                        if candle_low <= trail_stop:
                            exit_price = trail_stop
                            exit_reason = "trailing_stop"

                else:  # short
                    high_water_mark = min(high_water_mark, candle_low)
                    if cfg.stop_loss_pct and candle_high >= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        exit_reason = "stop_loss"
                    elif cfg.take_profit_pct and candle_low <= position["take_profit"]:
                        exit_price = position["take_profit"]
                        exit_reason = "take_profit"

                if exit_price:
                    trade, capital = self._close_position(position, exit_price, exit_reason, capital, candle)
                    trades.append(trade)
                    position = None
                    high_water_mark = 0.0

            # ── Generate strategy signal ──────────────────────────────────
            ctx = BotContext(
                bot_id="backtest",
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                candles=df.iloc[: i + 1],
                current_price=candle_close,
                position=position,
                paper_balance=capital,
                params=cfg.strategy_params,
            )
            signal: Signal = self.strategy.generate_signal(ctx)

            # ── Open position on buy signal ───────────────────────────────
            if signal.action == "buy" and not position and capital > 10:
                entry_price = candle_close * (1 + cfg.slippage_pct / 100)
                stop_loss = entry_price * (1 - (cfg.stop_loss_pct or 2) / 100)
                take_profit = entry_price * (1 + (cfg.take_profit_pct or 4) / 100)

                risk_amount = capital * (cfg.risk_per_trade_pct / 100)
                price_risk = entry_price - stop_loss
                quantity = (risk_amount / price_risk) if price_risk > 0 else 0

                if quantity > 0:
                    cost = quantity * entry_price
                    commission = cost * (cfg.commission_pct / 100)
                    if cost + commission <= capital:
                        capital -= commission
                        position = {
                            "side": "buy",
                            "entry_price": entry_price,
                            "quantity": quantity,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "entry_time": candle["timestamp"],
                            "entry_reason": signal.reason,
                        }
                        high_water_mark = entry_price

            # ── Close position on sell signal ─────────────────────────────
            elif signal.action == "sell" and position:
                exit_price = candle_close * (1 - cfg.slippage_pct / 100)
                trade, capital = self._close_position(position, exit_price, "signal", capital, candle)
                trades.append(trade)
                position = None

            # Track equity
            unrealized = 0.0
            if position:
                unrealized = (candle_close - position["entry_price"]) * position["quantity"]
            equity_curve.append(capital + unrealized)

        # Close any open position at the last candle
        if position:
            last_close = float(df.iloc[-1]["close"])
            trade, capital = self._close_position(position, last_close, "end_of_data", capital, df.iloc[-1])
            trades.append(trade)

        equity_curve.append(capital)
        return trades, equity_curve

    def _close_position(
        self,
        position: dict,
        exit_price: float,
        reason: str,
        capital: float,
        candle: pd.Series,
    ) -> tuple[BacktestTrade, float]:
        cfg = self.config
        qty = position["quantity"]
        entry = position["entry_price"]
        side = position["side"]

        gross_pnl = (exit_price - entry) * qty if side == "buy" else (entry - exit_price) * qty
        commission = exit_price * qty * (cfg.commission_pct / 100)
        net_pnl = gross_pnl - commission
        pnl_pct = (net_pnl / (entry * qty)) * 100

        new_capital = capital + (exit_price * qty) + net_pnl - (exit_price * qty)
        # Simpler: capital just gains/loses the PnL
        new_capital = capital + net_pnl

        trade = BacktestTrade(
            entry_time=position["entry_time"],
            exit_time=candle["timestamp"],
            symbol=cfg.symbol,
            side=side,
            entry_price=entry,
            exit_price=exit_price,
            quantity=qty,
            pnl_usdt=net_pnl,
            pnl_pct=pnl_pct,
            commission=commission,
            exit_reason=reason,
            entry_reason=position.get("entry_reason", ""),
        )
        return trade, new_capital

    def _compute_metrics(
        self,
        df: pd.DataFrame,
        trades: list[BacktestTrade],
        equity_curve: list[float],
    ) -> BacktestResult:
        cfg = self.config
        equity = np.array(equity_curve, dtype=float)
        final_capital = float(equity[-1])

        # ── Returns ────────────────────────────────────────────────────────
        total_return = (final_capital - cfg.initial_capital) / cfg.initial_capital * 100
        days = max((df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days, 1)
        annualized_return = ((final_capital / cfg.initial_capital) ** (365 / days) - 1) * 100

        # ── Drawdown ───────────────────────────────────────────────────────
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max * 100
        max_drawdown = float(np.min(drawdowns))

        # ── Sharpe / Sortino ───────────────────────────────────────────────
        daily_returns = np.diff(equity) / equity[:-1]
        sharpe = self._sharpe(daily_returns)
        sortino = self._sortino(daily_returns)
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        # ── Trade Stats ────────────────────────────────────────────────────
        winners = [t for t in trades if t.pnl_usdt > 0]
        losers = [t for t in trades if t.pnl_usdt <= 0]
        win_rate = len(winners) / len(trades) * 100 if trades else 0.0
        avg_win = np.mean([t.pnl_pct for t in winners]) if winners else 0.0
        avg_loss = np.mean([t.pnl_pct for t in losers]) if losers else 0.0

        gross_profit = sum(t.pnl_usdt for t in winners)
        gross_loss = abs(sum(t.pnl_usdt for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        expectancy = np.mean([t.pnl_usdt for t in trades]) if trades else 0.0

        # ── Build equity curve & drawdown series ─────────────────────────
        timestamps = df["timestamp"].iloc[49:].reset_index(drop=True)
        equity_series = [
            {"date": str(ts), "equity": round(eq, 2)}
            for ts, eq in zip(timestamps, equity_curve)
        ]
        drawdown_series = [
            {"date": str(ts), "drawdown_pct": round(float(dd), 4)}
            for ts, dd in zip(timestamps, drawdowns)
        ]

        trade_log = [
            {
                "entry_time": str(t.entry_time),
                "exit_time": str(t.exit_time),
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl_usdt": round(t.pnl_usdt, 2),
                "pnl_pct": round(t.pnl_pct, 4),
                "exit_reason": t.exit_reason,
            }
            for t in trades
        ]

        return BacktestResult(
            symbol=cfg.symbol,
            timeframe=cfg.timeframe,
            strategy=cfg.strategy_type,
            start_date=df["timestamp"].iloc[0],
            end_date=df["timestamp"].iloc[-1],
            initial_capital=cfg.initial_capital,
            final_capital=round(final_capital, 2),
            total_return_pct=round(total_return, 2),
            annualized_return_pct=round(annualized_return, 2),
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            max_drawdown_pct=round(max_drawdown, 2),
            calmar_ratio=round(calmar, 3),
            total_trades=len(trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate_pct=round(win_rate, 2),
            avg_win_pct=round(float(avg_win), 4),
            avg_loss_pct=round(float(avg_loss), 4),
            avg_risk_reward=round(avg_rr, 2),
            profit_factor=round(profit_factor, 3),
            expectancy_usdt=round(float(expectancy), 2),
            equity_curve=equity_series,
            drawdown_series=drawdown_series,
            trade_log=trade_log,
            trades=trades,
        )

    @staticmethod
    def _sharpe(returns: np.ndarray, risk_free: float = 0.0, periods: int = 252) -> float:
        excess = returns - risk_free / periods
        std = np.std(excess, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(periods))

    @staticmethod
    def _sortino(returns: np.ndarray, risk_free: float = 0.0, periods: int = 252) -> float:
        excess = returns - risk_free / periods
        downside = excess[excess < 0]
        downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 1e-10
        return float(np.mean(excess) / downside_std * np.sqrt(periods))
