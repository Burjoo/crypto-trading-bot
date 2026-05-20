"""
API v1 — Route aggregator.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    bots,
    backtest,
    exchanges,
    market,
    portfolio,
    trades,
    journal,
    alerts,
)

router = APIRouter()

router.include_router(auth.router,      prefix="/auth",      tags=["Authentication"])
router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchanges"])
router.include_router(bots.router,      prefix="/bots",      tags=["Bots"])
router.include_router(backtest.router,  prefix="/backtest",  tags=["Backtesting"])
router.include_router(market.router,    prefix="/market",    tags=["Market Data"])
router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
router.include_router(trades.router,    prefix="/trades",    tags=["Trades"])
router.include_router(journal.router,   prefix="/journal",   tags=["Journal"])
router.include_router(alerts.router,    prefix="/alerts",    tags=["Alerts"])
