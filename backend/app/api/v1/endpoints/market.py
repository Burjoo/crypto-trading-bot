"""Market data endpoints — live prices, tickers, OHLCV."""
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.models.models import User
from app.services.exchange_service import ExchangeService

router = APIRouter()
_svc = ExchangeService()

WATCHLIST = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
             "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "LINK/USDT"]


@router.get("/overview")
async def market_overview(_: Annotated[User, Depends(get_current_user)]):
    """Return ticker data for a default watchlist."""
    results = []
    for sym in WATCHLIST:
        try:
            ticker = await _svc.fetch_public_ohlcv("binance", sym, "1d", limit=2)
            if len(ticker) >= 2:
                prev, curr = ticker[-2], ticker[-1]
                chg_pct = (curr["close"] - prev["close"]) / prev["close"] * 100
                results.append({
                    "symbol": sym,
                    "price": curr["close"],
                    "change_pct_24h": round(chg_pct, 2),
                    "high_24h": curr["high"],
                    "low_24h": curr["low"],
                    "volume_24h": curr["volume"],
                })
        except Exception:
            pass
    return {"markets": results}


@router.get("/ohlcv")
async def get_ohlcv(
    _: Annotated[User, Depends(get_current_user)],
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 200,
    exchange: str = "binance",
):
    try:
        data = await _svc.fetch_public_ohlcv(exchange, symbol, timeframe, limit)
        return {"symbol": symbol, "timeframe": timeframe, "candles": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
