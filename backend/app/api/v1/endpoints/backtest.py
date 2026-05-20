"""
Backtesting Endpoint.
Runs strategies against historical data and returns full performance metrics.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.models import User
from app.services.backtest_engine import BacktestConfig, BacktestEngine
from app.services.exchange_service import ExchangeService

router = APIRouter()
exchange_svc = ExchangeService()


class BacktestRequest(BaseModel):
    strategy_type: str
    strategy_params: dict = Field(default_factory=dict)
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    exchange: str = Field(default="binance")
    limit: int = Field(default=500, ge=100, le=10_000)
    initial_capital: float = Field(default=10_000.0, gt=0)
    commission_pct: float = Field(default=0.1, ge=0, le=1)
    stop_loss_pct: Optional[float] = Field(default=2.0, gt=0, le=50)
    take_profit_pct: Optional[float] = Field(default=4.0, gt=0, le=200)
    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=10)


@router.post("/run")
async def run_backtest(
    payload: BacktestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Run a backtest for a given strategy and symbol.
    Returns full performance metrics, equity curve, and trade log.
    """
    # Fetch public OHLCV data
    try:
        ohlcv = await exchange_svc.fetch_public_ohlcv(
            exchange_name=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch market data: {str(exc)}"
        )

    if len(ohlcv) < 100:
        raise HTTPException(status_code=400, detail="Insufficient historical data")

    config = BacktestConfig(
        strategy_type=payload.strategy_type,
        strategy_params=payload.strategy_params,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        initial_capital=payload.initial_capital,
        commission_pct=payload.commission_pct,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        risk_per_trade_pct=payload.risk_per_trade_pct,
    )

    try:
        engine = BacktestEngine(config)
        result = engine.run(ohlcv)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(exc)}")

    return {
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "strategy": result.strategy,
        "period": {
            "start": str(result.start_date),
            "end": str(result.end_date),
        },
        "capital": {
            "initial": result.initial_capital,
            "final": result.final_capital,
        },
        "performance": {
            "total_return_pct": result.total_return_pct,
            "annualized_return_pct": result.annualized_return_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "calmar_ratio": result.calmar_ratio,
        },
        "trades": {
            "total": result.total_trades,
            "winning": result.winning_trades,
            "losing": result.losing_trades,
            "win_rate_pct": result.win_rate_pct,
            "avg_win_pct": result.avg_win_pct,
            "avg_loss_pct": result.avg_loss_pct,
            "avg_risk_reward": result.avg_risk_reward,
            "profit_factor": result.profit_factor,
            "expectancy_usdt": result.expectancy_usdt,
        },
        "equity_curve": result.equity_curve,
        "drawdown_series": result.drawdown_series,
        "trade_log": result.trade_log,
    }


@router.get("/strategies")
async def list_strategies(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return available strategy types with their default parameters."""
    from app.services.trading_engine import STRATEGY_REGISTRY
    return {
        "strategies": [
            {
                "type": key,
                "name": cls.name.replace("_", " ").title(),
                "default_params": cls.default_params,
            }
            for key, cls in STRATEGY_REGISTRY.items()
        ]
    }
