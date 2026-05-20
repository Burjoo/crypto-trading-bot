"""
Backend test suite.
Tests: security utilities, trading strategies, backtest engine, API auth flow.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from app.core.security import (
    hash_password, verify_password,
    create_access_token, verify_token,
    encrypt_api_key, decrypt_api_key,
)
from app.services.trading_engine import (
    MovingAverageCrossover, RSIStrategy, MACDStrategy, BreakoutStrategy,
    BotContext, get_strategy, RiskManager,
)
from app.services.backtest_engine import BacktestConfig, BacktestEngine


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_candles(n=200, trend="up") -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    close = 100.0
    rows = []
    for i in range(n):
        change = np.random.randn() * 0.5 + (0.05 if trend == "up" else -0.05)
        close = max(close + change, 1.0)
        high  = close + abs(np.random.randn() * 0.3)
        low   = close - abs(np.random.randn() * 0.3)
        rows.append({
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000 + i * 3600_000,
            "open":   close - np.random.randn() * 0.2,
            "high":   high,
            "low":    low,
            "close":  close,
            "volume": abs(np.random.randn() * 1000 + 5000),
        })
    return pd.DataFrame(rows)


def make_context(candles: pd.DataFrame, position=None) -> BotContext:
    return BotContext(
        bot_id="test",
        symbol="BTC/USDT",
        timeframe="1h",
        candles=candles,
        current_price=float(candles["close"].iloc[-1]),
        position=position,
        paper_balance=10_000.0,
        params={},
    )


# ─── Security Tests ────────────────────────────────────────────────────────────

class TestSecurity:
    def test_password_hash_verify(self):
        pw = "SuperSecret123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_access_token_roundtrip(self):
        token = create_access_token(subject="user-123")
        user_id = verify_token(token, "access")
        assert user_id == "user-123"

    def test_refresh_token_wrong_type(self):
        from app.core.security import create_refresh_token
        token = create_refresh_token("user-456")
        # Should not pass as access token
        result = verify_token(token, "access")
        assert result is None

    def test_api_key_encryption(self):
        secret = "my-exchange-api-secret-12345"
        encrypted = encrypt_api_key(secret)
        assert encrypted != secret
        assert decrypt_api_key(encrypted) == secret


# ─── Strategy Tests ───────────────────────────────────────────────────────────

class TestStrategies:
    def test_ma_crossover_signal_types(self):
        df = make_candles(100)
        strategy = MovingAverageCrossover({"fast_period": 5, "slow_period": 20})
        ctx = make_context(df)
        signal = strategy.generate_signal(ctx)
        assert signal.action in ("buy", "sell", "hold")
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.symbol == "BTC/USDT"

    def test_rsi_signal_with_insufficient_candles(self):
        df = make_candles(5)  # too few
        strategy = RSIStrategy()
        ctx = make_context(df)
        signal = strategy.generate_signal(ctx)
        assert signal.action == "hold"

    def test_macd_signal_types(self):
        df = make_candles(150)
        strategy = MACDStrategy()
        ctx = make_context(df)
        signal = strategy.generate_signal(ctx)
        assert signal.action in ("buy", "sell", "hold")

    def test_breakout_signal_types(self):
        df = make_candles(100)
        strategy = BreakoutStrategy()
        ctx = make_context(df)
        signal = strategy.generate_signal(ctx)
        assert signal.action in ("buy", "sell", "hold")

    def test_strategy_registry(self):
        for name in ["ma_crossover", "rsi", "macd", "breakout"]:
            strategy = get_strategy(name)
            assert strategy is not None

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent_strategy")


# ─── Risk Manager Tests ────────────────────────────────────────────────────────

class TestRiskManager:
    def setup_method(self):
        self.rm = RiskManager()

    def test_position_size_calculation(self):
        qty = self.rm.calculate_position_size(
            account_balance=10_000,
            risk_pct=1.0,
            entry_price=100.0,
            stop_loss_price=98.0,
        )
        # Risk = $100, price_risk = $2, qty = 50
        assert abs(qty - 50.0) < 0.01

    def test_stop_loss_buy(self):
        sl = self.rm.calculate_stop_loss(entry_price=100, side="buy", stop_loss_pct=2)
        assert sl == 98.0

    def test_stop_loss_sell(self):
        sl = self.rm.calculate_stop_loss(entry_price=100, side="sell", stop_loss_pct=2)
        assert sl == 102.0

    def test_take_profit_buy(self):
        tp = self.rm.calculate_take_profit(entry_price=100, side="buy", take_profit_pct=4)
        assert tp == 104.0

    def test_risk_reward_ratio(self):
        rr = self.rm.calculate_risk_reward(
            entry_price=100, stop_loss_price=98, take_profit_price=106
        )
        assert rr == 3.0  # 6/2

    def test_max_daily_loss_trigger(self):
        assert self.rm.check_max_daily_loss(-600, 500) == True
        assert self.rm.check_max_daily_loss(-400, 500) == False


# ─── Backtest Engine Tests ────────────────────────────────────────────────────

class TestBacktestEngine:
    def _run(self, strategy="ma_crossover", n=300):
        config = BacktestConfig(
            strategy_type=strategy,
            strategy_params={},
            symbol="BTC/USDT",
            timeframe="1h",
            initial_capital=10_000,
            commission_pct=0.1,
            stop_loss_pct=2.0,
            take_profit_pct=4.0,
            risk_per_trade_pct=1.0,
        )
        df = make_candles(n)
        engine = BacktestEngine(config)
        return engine.run(df.to_dict("records"))

    def test_backtest_completes(self):
        result = self._run("ma_crossover")
        assert result is not None
        assert result.initial_capital == 10_000

    def test_backtest_metrics_types(self):
        result = self._run("rsi")
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown_pct, float)
        assert isinstance(result.win_rate_pct, float)
        assert result.max_drawdown_pct <= 0  # always negative or zero

    def test_equity_curve_length(self):
        result = self._run("macd")
        assert len(result.equity_curve) > 0

    def test_trade_log_structure(self):
        result = self._run("breakout")
        for trade in result.trade_log:
            assert "entry_price" in trade
            assert "exit_price" in trade
            assert "pnl_usdt" in trade
            assert "exit_reason" in trade

    def test_insufficient_candles_raises(self):
        config = BacktestConfig(
            strategy_type="ma_crossover", strategy_params={},
            symbol="BTC/USDT", timeframe="1h",
        )
        engine = BacktestEngine(config)
        with pytest.raises(ValueError, match="at least 50 candles"):
            engine.run([{"timestamp": 0, "open":1,"high":1,"low":1,"close":1,"volume":1}] * 10)
